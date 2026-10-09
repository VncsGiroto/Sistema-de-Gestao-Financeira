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
    account_id: int | None = None  # conta INVESTMENT da corretora (vínculo de caixa)
    category_id: int | None = None
    rate_type: str | None = Field(default=None, pattern="^(CDI_PCT|PREFIXADO|IPCA_MAIS)$")
    rate: Decimal | None = Field(default=None, gt=Decimal("0"))
    maturity_date: date_t | None = None
    tax_rate: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"))  # IR esperado %


class AssetPatch(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    custodian: str | None = Field(default=None, max_length=80)
    account_id: int | None = None
    category_id: int | None = None
    rate_type: str | None = Field(default=None, pattern="^(CDI_PCT|PREFIXADO|IPCA_MAIS)$")
    rate: Decimal | None = Field(default=None, gt=Decimal("0"))
    maturity_date: date_t | None = None
    tax_rate: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"))


class AssetOut(BaseModel):
    id: int
    ticker: str
    name: str | None = None
    asset_class: str
    subtype: str
    custodian: str | None = None
    account_id: int | None = None
    currency: str
    category_id: int | None = None
    rate_type: str | None = None
    rate: Decimal | None = None
    maturity_date: date_t | None = None
    tax_rate: Decimal | None = None


class OpIn(BaseModel):
    kind: str = Field(pattern="^(APORTE|RESGATE|RENDIMENTO|REINVESTIMENTO)$")
    date: date_t
    quantity: Decimal | None = Field(default=None, gt=Decimal("0"))
    price: Decimal | None = Field(default=None, gt=Decimal("0"))
    fees: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    amount: Decimal | None = Field(default=None, gt=Decimal("0"))  # RENDIMENTO informa; RF com contrato opera em valor
    account_id: int | None = None  # RENDIMENTO: conta onde caiu (gera transação)
    category_id: int | None = None  # default: categoria do ativo
    full: bool = False  # RESGATE em RF com contrato: liquida a posição inteira (ignora amount)


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
    reinvestimentos: Decimal
    resgates: Decimal
    rendimentos: Decimal
    current_price: Decimal | None = None
    price_source: str | None = None  # ACCRUAL | MANUAL
    price_as_of: date_t | None = None
    current_value: Decimal | None = None
    pnl: Decimal | None = None
    profitability: Decimal | None = None  # simples; XIRR/TWR entram em 7.3
    net_value: Decimal | None = None  # líquido est. do resgate total (IR estimado)
    net_tax: Decimal | None = None  # IR estimado
    net_rate: Decimal | None = None  # alíquota % aplicada
    net_rate_source: str | None = None  # manual|auto


class PriceIn(BaseModel):
    date: date_t
    price: Decimal = Field(gt=Decimal("0"))
    override: bool = False  # exceção manual explícita p/ RF com contrato sem cotação


class PriceOut(BaseModel):
    id: int
    date: date_t
    price: Decimal
    source: str


class BenchmarksOut(BaseModel):
    cdi: Decimal | None = None
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


class PortfolioPositionOut(BaseModel):
    asset_id: int
    ticker: str
    asset_class: str
    account_id: int | None = None
    quantity: Decimal
    average_price: Decimal
    invested: Decimal
    current_price: Decimal | None = None
    price_source: str | None = None
    value: Decimal | None = None


class PortfolioSliceOut(BaseModel):
    name: str
    total: Decimal


class PortfolioAccountOut(BaseModel):
    account_id: int
    name: str
    cash: Decimal
    value: Decimal


class PortfolioSnapshotOut(BaseModel):
    date: date_t
    cash: Decimal
    positions_value: Decimal | None = None
    total: Decimal | None = None
    status: str = "UNKNOWN"
    unpriced: list[str] = []
    gain: Decimal | None = None  # ganho acumulado desde o 1º ponto COMPLETE (total − aportes líquidos)


class PortfolioOut(BaseModel):
    cash: Decimal
    positions_value: Decimal | None = None
    total: Decimal | None = None
    patrimonio: Decimal | None = None
    status: str = "UNKNOWN"
    aportes: Decimal
    reinvestimentos: Decimal
    resgates: Decimal
    rendimentos: Decimal
    net_invested: Decimal
    resultado: Decimal | None = None
    xirr: Decimal | None = None
    twr: Decimal | None = None
    positions: list[PortfolioPositionOut]
    unpriced: list[str]
    by_class: list[PortfolioSliceOut]
    by_account: list[PortfolioAccountOut]
    snapshots: list[PortfolioSnapshotOut]
    history_since: date_t | None = None
