from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bills.models import RecurringBill


async def list_all(session: AsyncSession, user_id: int) -> list[RecurringBill]:
    res = await session.execute(
        select(RecurringBill).where(RecurringBill.user_id == user_id).order_by(RecurringBill.id)
    )
    return list(res.scalars().all())


async def upcoming(session: AsyncSession, user_id: int, days: int) -> list[RecurringBill]:
    limit = date.today().fromordinal(date.today().toordinal() + days)
    res = await session.execute(
        select(RecurringBill)
        .where(RecurringBill.user_id == user_id, RecurringBill.next_due.is_not(None), RecurringBill.next_due <= limit)
        .order_by(RecurringBill.next_due)
    )
    return list(res.scalars().all())


async def get_one(session: AsyncSession, user_id: int, bill_id: int) -> RecurringBill | None:
    res = await session.execute(
        select(RecurringBill).where(RecurringBill.id == bill_id, RecurringBill.user_id == user_id)
    )
    return res.scalar_one_or_none()


async def create(session: AsyncSession, row: RecurringBill) -> RecurringBill:
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def delete(session: AsyncSession, row: RecurringBill) -> None:
    await session.delete(row)
    await session.commit()
