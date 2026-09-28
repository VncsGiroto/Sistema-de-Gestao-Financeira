from datetime import date as date_t
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TimestampMixin


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("account_type IN ('CHECKING','SAVINGS','CREDIT_CARD','CASH','OTHER')", name="ck_accounts_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    bank: Mapped[str | None] = mapped_column(String(120), nullable=True)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("type IN ('INCOME','EXPENSE')", name="ck_categories_type"),
        UniqueConstraint("user_id", "name", "type", name="uq_categories_user_name_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("type IN ('INCOME','EXPENSE')", name="ck_tx_type"),
        CheckConstraint("source IN ('MANUAL','OFX','IMPORT','PAYABLE')", name="ck_tx_source"),
        CheckConstraint("amount <> 0", name="ck_tx_amount"),
        UniqueConstraint("user_id", "source", "external_id", name="uq_tx_user_source_external"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    date: Mapped[date_t] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    import_id: Mapped[int | None] = mapped_column(
        ForeignKey("imports.id", ondelete="SET NULL"), nullable=True
    )  # Épico 3
    payable_id: Mapped[int | None] = mapped_column(
        ForeignKey("payables.id", ondelete="SET NULL"), nullable=True
    )  # baixa de contas a pagar
