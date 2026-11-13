from django.contrib import admin

from .models import IdempotencyKey, Transfer, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance")


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ("id", "from_wallet", "to_wallet", "amount", "created_at")


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "response_status", "created_at")