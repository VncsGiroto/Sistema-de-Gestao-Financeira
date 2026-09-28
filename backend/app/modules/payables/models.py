from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Payable(Base):
    __tablename__ = "payables"
    __table_args__ = (
        CheckConstraint("kind IN ('FIXED','RECURRING','INSTALLMENT','ONE_TIME')", name="ck_pay_kind"),
        CheckConstraint("due_day IS NULL OR due_day BETWEEN 1 AND 31", name="ck_pay_due_day"),
        CheckConstraint("num_installments IS NULL OR num_installments BETWEEN 2 AND 60", name="ck_pay_num"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    periodicity: Mapped[str | None] = mapped_column(String(10), nullable=True)
    due_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    num_installments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    installment_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    first_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_ns: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
