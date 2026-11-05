import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet"
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        constraints = [
            # DB-level safety net: balance can never go negative
            models.CheckConstraint(
                condition=Q(balance__gte=0), name="wallet_balance_non_negative"
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.balance}"


class Transfer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_wallet = models.ForeignKey(
        Wallet, on_delete=models.PROTECT, related_name="sent_transfers"
    )
    to_wallet = models.ForeignKey(
        Wallet, on_delete=models.PROTECT, related_name="received_transfers"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class IdempotencyKey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key = models.CharField(max_length=100)
    request_hash = models.CharField(max_length=64)
    response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # This unique constraint is what makes idempotency safe under concurrency
            models.UniqueConstraint(
                fields=["user", "key"], name="unique_idempotency_key_per_user"
            ),
        ]