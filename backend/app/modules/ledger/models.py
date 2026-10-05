from datetime import date as date_t
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TimestampMixin


class LedgerMovement(Base, TimestampMixin):
    """Ledger canônico de movimentações patrimoniais (épico investimentos↔contas).

    TRANSFER: origem+destino, sem op. APORTE: caixa→posição (from=conta, to=NULL).
    RESGATE: posição→caixa (from=NULL, to=conta). REINVESTIMENTO: interno (contas NULL).
    Nunca toca income/expense: saldos e patrimônio derivam daqui + transactions.
    """

    __tablename__ = "ledger_movements"
    __table_args__ = (
        CheckConstraint("kind IN ('TRANSFER','APORTE','RESGATE','REINVESTIMENTO')", name="ck_led_kind"),
        CheckConstraint("amount > 0", name="ck_led_amount"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    from_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True)
    to_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    date: Mapped[date_t] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="Transferência")
    op_id: Mapped[int | None] = mapped_column(
        ForeignKey("investment_ops.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=True)
