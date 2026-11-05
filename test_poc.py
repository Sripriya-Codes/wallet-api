import threading
import uuid

import requests

BASE = "http://127.0.0.1:8000/api"
PASSWORD = "Pass@12345"


def register(username):
    r = requests.post(
        f"{BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": PASSWORD},
    )
    print("register", username, r.status_code)


def login(username):
    r = requests.post(f"{BASE}/auth/login", json={"username": username, "password": PASSWORD})
    return r.json()["access"]


def balance(token):
    r = requests.get(f"{BASE}/wallet/me", headers={"Authorization": f"Bearer {token}"})
    return r.json()["balance"]


def transfer(token, to, amount, key, simulate_failure=False):
    return requests.post(
        f"{BASE}/wallet/transfer",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": key},
        json={"to_username": to, "amount": amount, "simulate_failure": simulate_failure},
    )


suffix = uuid.uuid4().hex[:6]
alice, bob = f"alice_{suffix}", f"bob_{suffix}"
register(alice)
register(bob)
alice_token = login(alice)
bob_token = login(bob)

print("\n--- 0. JWT: no token should be rejected ---")
print(requests.get(f"{BASE}/wallet/me").status_code, "(expect 401)")

print("\n--- 1. Normal transfer ---")
key1 = str(uuid.uuid4())
r = transfer(alice_token, bob, "100.00", key1)
print(r.status_code, r.json())
print("alice:", balance(alice_token), "bob:", balance(bob_token), "(expect 900 / 1100)")

print("\n--- 2. Same key + same body again: replay, no double debit ---")
r = transfer(alice_token, bob, "100.00", key1)
print(r.status_code, r.headers.get("Idempotent-Replayed"), r.json())
print("alice:", balance(alice_token), "(expect still 900)")

print("\n--- 3. Same key + different body: rejected ---")
r = transfer(alice_token, bob, "500.00", key1)
print(r.status_code, r.json(), "(expect 422)")

print("\n--- 4. Rollback: crash after debit ---")
try:
    r = transfer(alice_token, bob, "50.00", str(uuid.uuid4()), simulate_failure=True)
    print(r.status_code, "(expect 500)")
except Exception as e:
    print("error", e)
print("alice:", balance(alice_token), "(expect still 900, rolled back)")

print("\n--- 5. Insufficient funds ---")
r = transfer(alice_token, bob, "99999.00", str(uuid.uuid4()))
print(r.status_code, r.json(), "(expect 400)")

print("\n--- 6. Concurrency: 5 parallel requests, same key ---")
key6 = str(uuid.uuid4())
results = []


def worker():
    results.append(transfer(alice_token, bob, "10.00", key6).status_code)


threads = [threading.Thread(target=worker) for _ in range(5)]
[t.start() for t in threads]
[t.join() for t in threads]
print("statuses:", sorted(results), "(exactly one 201, the rest 201 replay or 409)")
print("alice:", balance(alice_token), "(expect 890, debited only once)")