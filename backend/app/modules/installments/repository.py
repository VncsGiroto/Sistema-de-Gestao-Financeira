from datetime import date
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance.models import Account
from app.modules.installments.models import Installment
from app.modules.installments.schedule import schedule


async def owned_account(session: AsyncSession, user_id: int, account_id: int | None):
    if account_id is None:
        return None
    res = await session.execute(select(Account).where(Account.id == account_id, Account.user_id == user_id))
    return res.scalar_one_or_none()


async def list_all(session: AsyncSession, user_id: int) -> list[Installment]:
    res = await session.execute(select(Installment).where(Installment.user_id == user_id).order_by(Installment.id))
    return list(res.scalars().all())


async def get_one(session: AsyncSession, user_id: int, inst_id: int) -> Installment | None:
    res = await session.execute(select(Installment).where(Installment.id == inst_id, Installment.user_id == user_id))
    return res.scalar_one_or_none()


async def create(
    session: AsyncSession,
    user_id: int,
    description: str,
    total: Decimal,
    n: int,
    first_due: date,
    account_id: int | None,
) -> Installment | None:
    """Retorna None se a conta não pertencer ao usuário."""
    if await owned_account(session, user_id, account_id) is None and account_id is not None:
        return None
    base = (total / n).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    row = Installment(
        user_id=user_id,
        description=description.strip(),
        total_amount=total,
        num_installments=n,
        installment_amount=base,
        first_due_date=first_due,
        account_id=account_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def delete(session: AsyncSession, row: Installment) -> None:
    await session.delete(row)
    await session.commit()


def build_schedule(row: Installment) -> list[dict]:
    return schedule(row.total_amount, row.num_installments, row.first_due_date)
