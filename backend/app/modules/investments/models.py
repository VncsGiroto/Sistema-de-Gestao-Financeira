from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "asset_class IN ('RENDA_FIXA','RENDA_VARIAVEL','FUNDOS','CRIPTO','OUTROS')", name="ck_asset_class"
        ),
        UniqueConstraint("user_id", "ticker", "account_id", name="uq_assets_user_ticker_account"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False)
    subtype: Mapped[str] = mapped_column(String(20), nullable=False)
    custodian: Mapped[str | None] = mapped_column(String(80), nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    rate_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # CDI_PCT|PREFIXADO|IPCA_MAIS
    rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)  # % (pct do CDI ou a.a.)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class InvestmentOp(Base):
    __tablename__ = "investment_ops"
    __table_args__ = (
        CheckConstraint("kind IN ('APORTE','RESGATE','RENDIMENTO','REINVESTIMENTO')", name="ck_op_kind"),
        CheckConstraint("amount > 0", name="ck_op_amount"),
        CheckConstraint("fees >= 0", name="ck_op_fees"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    fees: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PortfolioSnapshot(Base):
    """Valor consolidado da carteira (caixa de investimento + posições) por dia.

    Gravado sob evento (op criada/excluída, preço manual). Série esparsa: o gráfico
    mostra pontos reais com lacunas explícitas, sem interpolação.
    """

    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_snap_user_date"),
        CheckConstraint("status IN ('COMPLETE','INCOMPLETE','UNKNOWN')", name="ck_snap_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    positions_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="UNKNOWN")
    unpriced: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
