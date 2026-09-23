from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CommitmentItem(BaseModel):
    kind: str  # bill | installment
    description: str
    due_date: date
    amount: Decimal
    ref_id: int


class CommitmentsOut(BaseModel):
    total: Decimal
    items: list[CommitmentItem]
