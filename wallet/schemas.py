from decimal import Decimal

from ninja import Schema
from pydantic import Field


class TransferIn(Schema):
    to_username: str
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    # Demo only: crashes AFTER debiting, to prove the rollback works. Remove later.
    simulate_failure: bool = False


class WalletOut(Schema):
    username: str
    balance: Decimal