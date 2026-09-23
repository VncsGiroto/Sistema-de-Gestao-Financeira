from datetime import date as date_t
from decimal import Decimal

from pydantic import BaseModel, Field


class InstallmentIn(BaseModel):
    description: str = Field(min_length=2, max_length=200)
    total_amount: Decimal = Field(gt=Decimal("0"), le=Decimal("9999999999.99"))
    num_installments: int = Field(ge=2, le=60)
    first_due_date: date_t
    account_id: int | None = None


class InstallmentPatch(BaseModel):
    description: str | None = Field(default=None, min_length=2, max_length=200)
    account_id: int | None = None


class InstallmentOut(BaseModel):
    id: int
    description: str
    total_amount: Decimal
    num_installments: int
    installment_amount: Decimal
    first_due_date: date_t
    account_id: int | None


class ScheduleItem(BaseModel):
    n: int
    due_date: date_t
    amount: Decimal
