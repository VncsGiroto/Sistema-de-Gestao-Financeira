from datetime import date as date_t
from decimal import Decimal

from pydantic import BaseModel, Field


class TransferIn(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal = Field(gt=Decimal("0"), le=Decimal("9999999999.99"))
    date: date_t | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)


class MovementOut(BaseModel):
    id: int
    from_account_id: int | None
    to_account_id: int | None
    kind: str
    amount: Decimal
    date: date_t
    description: str
    op_id: int | None = None
    asset_id: int | None = None
