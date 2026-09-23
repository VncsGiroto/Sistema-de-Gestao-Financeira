from decimal import Decimal

from pydantic import BaseModel


class ByCategory(BaseModel):
    name: str
    total: Decimal


class Side(BaseModel):
    total: Decimal
    by_category: list[ByCategory]


class EvoItem(BaseModel):
    month: str
    income: Decimal
    expense: Decimal


class DashboardOut(BaseModel):
    balance: Decimal
    income: Side
    expense: Side
    evolution: list[EvoItem]
