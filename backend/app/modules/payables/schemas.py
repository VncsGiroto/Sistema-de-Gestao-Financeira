from datetime import date as date_t
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PayableIn(BaseModel):
    description: str = Field(min_length=2, max_length=200)
    kind: str = Field(pattern="^(FIXED|RECURRING|INSTALLMENT|ONE_TIME)$")
    amount: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("9999999999.99"))
    periodicity: str | None = Field(default=None, pattern="^(MONTHLY|WEEKLY|YEARLY)$")
    due_day: int | None = Field(default=None, ge=1, le=31)
    next_due: date_t | None = None
    total_amount: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("9999999999.99"))
    num_installments: int | None = Field(default=None, ge=2, le=60)
    first_due_date: date_t | None = None
    account_id: int | None = None
    category_id: int | None = None


class PayablePatch(BaseModel):
    description: str | None = Field(default=None, min_length=2, max_length=200)
    amount: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("9999999999.99"))
    next_due: date_t | None = None  # só ONE_TIME
    account_id: int | None = None
    category_id: int | None = None


class PayableOut(BaseModel):
    id: int
    description: str
    kind: str
    amount: Decimal | None = None
    periodicity: str | None = None
    due_day: int | None = None
    next_due: date_t | None = None
    total_amount: Decimal | None = None
    num_installments: int | None = None
    installment_amount: Decimal | None = None
    first_due_date: date_t | None = None
    paid_ns: list[int] = []
    paid_at: datetime | None = None
    account_id: int | None = None
    category_id: int | None = None


class ScheduleItemOut(BaseModel):
    n: int
    due_date: date_t
    amount: Decimal
    paid: bool = False


class PayIn(BaseModel):
    account_id: int
    amount: Decimal | None = Field(default=None, gt=Decimal("0"), le=Decimal("9999999999.99"))
    date: date_t | None = None
    category_id: int | None = None
    ns: list[int] | None = None  # INSTALLMENT: parcelas a pagar (default: próxima não-paga)
    discount: Decimal | None = Field(default=None, ge=Decimal("0"))


class PayTxOut(BaseModel):
    id: int
    description: str
    amount: Decimal
    date: date_t


class PayOut(BaseModel):
    transactions: list[PayTxOut]
    payable: PayableOut
