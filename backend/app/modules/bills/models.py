from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RecurringBill(Base):
    __tablename__ = "recurring_bills"
    __table_args__ = (
        CheckConstraint("kind IN ('FIXED','VARIABLE','ONE_TIME','RECURRING')", name="ck_bills_kind"),
        CheckConstraint("periodicity IN ('MONTHLY','WEEKLY','YEARLY')", name="ck_bills_periodicity"),
        CheckConstraint("due_day BETWEEN 1 AND 31", name="ck_bills_due_day"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    periodicity: Mapped[str | None] = mapped_column(String(10), nullable=True)
    due_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_due: Mapped[date | None] = mapped_column(Date, nullable=True)
