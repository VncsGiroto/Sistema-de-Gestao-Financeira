from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CommitmentItem(BaseModel):
    kind: str  # bill | installment
    description: str
    due_date: date
    amount: Decimal
    ref_id: int
    account_id: int | None = None


class CommitmentsOut(BaseModel):
    total: Decimal
    items: list[CommitmentItem]
    unassigned_total: Decimal = Decimal("0")
