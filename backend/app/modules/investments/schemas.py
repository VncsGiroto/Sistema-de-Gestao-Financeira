from datetime import date as date_t
from decimal import Decimal

from pydantic import BaseModel, Field

CLASSES = ("RENDA_FIXA", "RENDA_VARIAVEL", "FUNDOS", "CRIPTO", "OUTROS")


class AssetIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    name: str | None = Field(default=None, max_length=120)
    asset_class: str = Field(pattern="^(RENDA_FIXA|RENDA_VARIAVEL|FUNDOS|CRIPTO|OUTROS)$")
    subtype: str = Field(min_length=1, max_length=20)
    custodian: str | None = Field(default=None, max_length=80)
    category_id: int | None = None
    rate_type: str | None = Field(default=None, pattern="^(CDI_PCT|PREFIXADO|IPCA_MAIS)$")
    rate: Decimal | None = Field(default=None, gt=Decimal("0"))
    maturity_date: date_t | None = None


class AssetPatch(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    custodian: str | None = Field(default=None, max_length=80)
    category_id: int | None = None
    rate_type: str | None = Field(default=None, pattern="^(CDI_PCT|PREFIXADO|IPCA_MAIS)$")
    rate: Decimal | None = Field(default=None, gt=Decimal("0"))
    maturity_date: date_t | None = None


class AssetOut(BaseModel):
    id: int
    ticker: str
    name: str | None = None
    asset_class: str
    subtype: str
    custodian: str | None = None
    currency: str
    category_id: int | None = None
    rate_type: str | None = None
    rate: Decimal | None = None
    maturity_date: date_t | None = None


class OpIn(BaseModel):
    kind: str = Field(pattern="^(APORTE|RESGATE|RENDIMENTO)$")
    date: date_t
    quantity: Decimal | None = Field(default=None, gt=Decimal("0"))
    price: Decimal | None = Field(default=None, gt=Decimal("0"))
    fees: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    amount: Decimal | None = Field(default=None, gt=Decimal("0"))  # só RENDIMENTO informa
    account_id: int | None = None  # RENDIMENTO: conta onde caiu (gera transação)
    category_id: int | None = None  # default: categoria do ativo


class OpOut(BaseModel):
    id: int
    asset_id: int
    kind: str
    date: date_t
    quantity: Decimal | None = None
    price: Decimal | None = None
    fees: Decimal
    amount: Decimal
    transaction_id: int | None = None


class PositionOut(BaseModel):
    asset_id: int
    quantity: Decimal
    average_price: Decimal
    invested: Decimal
    aportes: Decimal
    resgates: Decimal
    rendimentos: Decimal
    current_price: Decimal | None = None
    price_source: str | None = None  # BRAPI | ACCRUAL | MANUAL
    price_as_of: date_t | None = None
    current_value: Decimal | None = None
    pnl: Decimal | None = None
    profitability: Decimal | None = None  # simples; XIRR/TWR entram em 7.3


class PriceIn(BaseModel):
    date: date_t
    price: Decimal = Field(gt=Decimal("0"))


class PriceOut(BaseModel):
    id: int
    date: date_t
    price: Decimal
    source: str


class BenchmarksOut(BaseModel):
    cdi: Decimal | None = None
    ibov: Decimal | None = None
    ipca: Decimal | None = None


class ReturnsOut(BaseModel):
    asset_id: int
    start: date_t | None = None
    end: date_t
    simple: Decimal | None = None
    xirr: Decimal | None = None
    twr: Decimal | None = None
    twr_annualized: Decimal | None = None
    benchmarks: BenchmarksOut = BenchmarksOut()
