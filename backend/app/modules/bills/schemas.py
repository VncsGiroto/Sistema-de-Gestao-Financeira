from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class BillIn(BaseModel):
    description: str = Field(min_length=2, max_length=200)
    amount: Decimal = Field(gt=Decimal("0"), le=Decimal("9999999999.99"))
    kind: str = Field(pattern="^(FIXED|VARIABLE|ONE_TIME|RECURRING)$")
    periodicity: str | None = Field(default=None, pattern="^(MONTHLY|WEEKLY|YEARLY)$")
    due_day: int | None = Field(default=None, ge=1, le=31)
    next_due: date | None = None


class BillPatch(BaseModel):
    description: str | None = Field(default=None, min_length=2, max_length=200)
    amount: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("9999999999.99"))
    next_due: date | None = None


class BillOut(BaseModel):
    id: int
    description: str
    amount: Decimal
    kind: str
    periodicity: str | None = None
    due_day: int | None = None
    next_due: date | None = None
