from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Transfer, Wallet


class TransferError(Exception):
    """Business-rule failure (insufficient funds, unknown recipient, etc.)"""


def do_transfer(sender_user, to_username: str, amount: Decimal, simulate_failure=False) -> dict:
    User = get_user_model()
    try:
        recipient = User.objects.get(username=to_username)
    except User.DoesNotExist:
        raise TransferError("Recipient not found")

    if recipient.pk == sender_user.pk:
        raise TransferError("Cannot transfer to yourself")

    # TRANSACTION: everything inside commits together, or everything rolls back
    with transaction.atomic():
        # select_for_update locks both rows. order_by("id") makes every request lock
        # in the same order, which prevents deadlocks.
        wallets = {
            w.user_id: w
            for w in Wallet.objects.select_for_update()
            .filter(user_id__in=[sender_user.pk, recipient.pk])
            .order_by("id")
        }
        sender_wallet = wallets.get(sender_user.pk)
        recipient_wallet = wallets.get(recipient.pk)
        if not sender_wallet or not recipient_wallet:
            raise TransferError("Wallet not found")

        if sender_wallet.balance < amount:
            raise TransferError("Insufficient funds")

        sender_wallet.balance -= amount
        sender_wallet.save(update_fields=["balance"])

        if simulate_failure:
            # The debit above is already saved, but the whole block rolls back
            raise RuntimeError("Simulated crash after debit")

        recipient_wallet.balance += amount
        recipient_wallet.save(update_fields=["balance"])

        transfer = Transfer.objects.create(
            from_wallet=sender_wallet, to_wallet=recipient_wallet, amount=amount
        )

    return {
        "transfer_id": str(transfer.id),
        "from": sender_user.username,
        "to": recipient.username,
        "amount": str(amount),
        "sender_new_balance": str(sender_wallet.balance),
    }