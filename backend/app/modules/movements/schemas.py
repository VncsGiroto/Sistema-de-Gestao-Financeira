from datetime import date as date_t
from decimal import Decimal

from pydantic import BaseModel, Field


class MovementItem(BaseModel):
    id: str  # tx:{id} | ledger:{id} | op:{id} — identidade estável para chaves e ações
    kind: str  # INCOME|EXPENSE|TRANSFER|APORTE|RESGATE|RENDIMENTO|REINVESTIMENTO
    date: date_t
    description: str
    amount: Decimal
    direction: str  # in|out|neutral (no contexto da conta filtrada; sem conta, efeito absoluto)
    cash_impact: Decimal  # +amount (in), −amount (out), 0 (neutral)
    account_id: int | None = None  # conta do lançamento / lado filtrado
    from_account_id: int | None = None
    to_account_id: int | None = None
    asset_id: int | None = None
    ticker: str | None = None
    op_id: int | None = None
    transaction_id: int | None = None
    movement_id: int | None = None
    category_id: int | None = None  # só lançamentos de receita/despesa (edição inline)
    editable: bool  # ação direta permitida (manual) ou só pela origem
    origin: str  # transaction|operation|transfer
    origin_hint: str


class MovementPageMeta(BaseModel):
    page: int
    per_page: int
    total: int


class MovementPage(BaseModel):
    data: list[MovementItem]
    meta: MovementPageMeta


class MovementFilters(BaseModel):
    from_: date_t | None = Field(default=None)
    to: date_t | None = Field(default=None)
    account_id: int | None = Field(default=None)
    kinds: list[str] = Field(default_factory=list)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
