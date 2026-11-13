from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from wallet.models import Transfer, Wallet
from wallet.services import do_transfer

User = get_user_model()
PASSWORD = "Pass@12345"
JSON = "application/json"


@pytest.fixture
def client():
    return Client()


def register(client, username):
    return client.post(
        "/api/auth/register",
        {"username": username, "email": f"{username}@test.com", "password": PASSWORD},
        content_type=JSON,
    )


def login(client, username, password=PASSWORD):
    return client.post(
        "/api/auth/login",
        {"username": username, "password": password},
        content_type=JSON,
    )


def send(client, token, to, amount, key):
    return client.post(
        "/api/wallet/transfer",
        {"to_username": to, "amount": amount},
        content_type=JSON,
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": key},
    )


def balance(username):
    return Wallet.objects.get(user__username=username).balance


@pytest.fixture
def alice_token(client, db):
    register(client, "alice")
    register(client, "bob")
    return login(client, "alice").json()["access"]


# ---------- JWT ----------

def test_login_returns_tokens(client, alice_token):
    assert alice_token


def test_login_wrong_password_returns_401(client, alice_token):
    assert login(client, "alice", "wrong-password").status_code == 401


def test_wallet_without_token_returns_401(client, alice_token):
    assert client.get("/api/wallet/me").status_code == 401


def test_refresh_token_cannot_be_used_as_access(client, alice_token):
    refresh = login(client, "alice").json()["refresh"]
    r = client.get("/api/wallet/me", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 401


# ---------- Transactions ----------

def test_register_creates_user_and_wallet(client, alice_token):
    assert balance("alice") == Decimal("1000.00")


def test_transfer_moves_money(client, alice_token):
    r = send(client, alice_token, "bob", "100.00", "k1")
    assert r.status_code == 201
    assert balance("alice") == Decimal("900.00")
    assert balance("bob") == Decimal("1100.00")


def test_insufficient_funds_leaves_balances_unchanged(client, alice_token):
    r = send(client, alice_token, "bob", "99999.00", "k2")
    assert r.status_code == 400
    assert balance("alice") == Decimal("1000.00")
    assert balance("bob") == Decimal("1000.00")


def test_failure_after_debit_rolls_back_everything(client, alice_token):
    alice = User.objects.get(username="alice")
    with patch("wallet.services.Transfer.objects.create", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            do_transfer(alice, "bob", Decimal("50.00"))
    assert balance("alice") == Decimal("1000.00")
    assert balance("bob") == Decimal("1000.00")
    assert Transfer.objects.count() == 0


# ---------- Idempotency ----------

def test_same_key_same_body_replays_and_debits_once(client, alice_token):
    first = send(client, alice_token, "bob", "100.00", "k3")
    second = send(client, alice_token, "bob", "100.00", "k3")
    assert first.status_code == 201
    assert second.status_code == 201
    assert second["Idempotent-Replayed"] == "true"
    assert first.json() == second.json()
    assert balance("alice") == Decimal("900.00")
    assert Transfer.objects.count() == 1


def test_same_key_different_body_returns_422(client, alice_token):
    send(client, alice_token, "bob", "100.00", "k4")
    r = send(client, alice_token, "bob", "500.00", "k4")
    assert r.status_code == 422
    assert balance("alice") == Decimal("900.00")