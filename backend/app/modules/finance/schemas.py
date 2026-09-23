from datetime import date as date_t
from decimal import Decimal

from pydantic import BaseModel, Field


class AccountIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    bank: str | None = Field(default=None, max_length=120)
    account_type: str = Field(pattern="^(CHECKING|SAVINGS|CREDIT_CARD|CASH|OTHER)$")
    initial_balance: Decimal = Field(default=Decimal("0"), ge=Decimal("-9999999999.99"), le=Decimal("9999999999.99"))


class AccountPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    bank: str | None = Field(default=None, max_length=120)
    account_type: str | None = Field(default=None, pattern="^(CHECKING|SAVINGS|CREDIT_CARD|CASH|OTHER)$")


class AccountOut(BaseModel):
    id: int
    name: str
    bank: str | None
    account_type: str
    initial_balance: Decimal


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    type: str = Field(pattern="^(INCOME|EXPENSE)$")


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)


class CategoryOut(BaseModel):
    id: int
    name: str
    type: str


class TxIn(BaseModel):
    account_id: int
    category_id: int | None = None
    date: date_t
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(ge=Decimal("-9999999999.99"), le=Decimal("9999999999.99"))
    type: str = Field(pattern="^(INCOME|EXPENSE)$")

    def model_post_init(self, _ctx) -> None:
        if self.amount == 0:
            raise ValueError("amount não pode ser zero")


class TxPatch(BaseModel):
    account_id: int | None = None
    category_id: int | None = None
    date: date_t | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)
    amount: Decimal | None = Field(default=None, ge=Decimal("-9999999999.99"), le=Decimal("9999999999.99"))
    type: str | None = Field(default=None, pattern="^(INCOME|EXPENSE)$")

    def model_post_init(self, _ctx) -> None:
        if self.amount is not None and self.amount == 0:
            raise ValueError("amount não pode ser zero")


class TxOut(BaseModel):
    id: int
    account_id: int
    category_id: int | None
    date: date_t
    description: str
    amount: Decimal
    type: str
    source: str


class PageMeta(BaseModel):
    page: int
    per_page: int
    total: int


class TxPage(BaseModel):
    data: list[TxOut]
    meta: PageMeta
