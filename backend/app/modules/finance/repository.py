from datetime import date as date_t
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import conflict
from app.modules.finance.models import Account, Category, Transaction


# --- accounts (sempre filtrados por user_id) ---
async def list_accounts(session: AsyncSession, user_id: int) -> list[Account]:
    res = await session.execute(select(Account).where(Account.user_id == user_id).order_by(Account.id))
    return list(res.scalars().all())


async def get_account(session: AsyncSession, user_id: int, account_id: int) -> Account | None:
    res = await session.execute(select(Account).where(Account.id == account_id, Account.user_id == user_id))
    return res.scalar_one_or_none()


async def create_account(session: AsyncSession, user_id: int, **data) -> Account:
    row = Account(user_id=user_id, **data)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def delete_account(session: AsyncSession, row: Account) -> None:
    await session.delete(row)
    await session.commit()


# --- categories ---
async def list_categories(session: AsyncSession, user_id: int, type_: str | None = None) -> list[Category]:
    q = select(Category).where(Category.user_id == user_id)
    if type_:
        q = q.where(Category.type == type_)
    res = await session.execute(q.order_by(Category.name))
    return list(res.scalars().all())


async def get_category(session: AsyncSession, user_id: int, category_id: int) -> Category | None:
    res = await session.execute(select(Category).where(Category.id == category_id, Category.user_id == user_id))
    return res.scalar_one_or_none()


async def create_category(session: AsyncSession, user_id: int, name: str, type_: str) -> Category:
    row = Category(user_id=user_id, name=name.strip(), type=type_)
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise conflict("Categoria já existe para este tipo")
    await session.refresh(row)
    return row


async def delete_category(session: AsyncSession, row: Category) -> None:
    await session.delete(row)
    await session.commit()


class TxFilters:
    def __init__(
        self,
        from_: date_t | None = None,
        to: date_t | None = None,
        account_id: int | None = None,
        category_id: int | None = None,
        type_: str | None = None,
        source: str | None = None,
        q: str | None = None,
        min_: Decimal | None = None,
        max_: Decimal | None = None,
    ):
        self.from_ = from_
        self.to = to
        self.account_id = account_id
        self.category_id = category_id
        self.type_ = type_
        self.source = source
        self.q = q
        self.min_ = min_
        self.max_ = max_

    def apply(self, q):
        if self.from_:
            q = q.where(Transaction.date >= self.from_)
        if self.to:
            q = q.where(Transaction.date <= self.to)
        if self.account_id:
            q = q.where(Transaction.account_id == self.account_id)
        if self.category_id:
            q = q.where(Transaction.category_id == self.category_id)
        if self.type_:
            q = q.where(Transaction.type == self.type_)
        if self.source:
            q = q.where(Transaction.source == self.source)
        if self.q:
            q = q.where(Transaction.description.ilike(f"%{self.q}%"))
        if self.min_ is not None:
            q = q.where(Transaction.amount >= self.min_)
        if self.max_ is not None:
            q = q.where(Transaction.amount <= self.max_)
        return q


async def create_tx(
    session: AsyncSession,
    user_id: int,
    account_id: int,
    category_id: int | None,
    date: date_t,
    description: str,
    amount: Decimal,
    type_: str,
) -> Transaction:
    # account/category precisam pertencer ao usuário (404 genérico, sem vazar)
    acc = await get_account(session, user_id, account_id)
    if acc is None:
        raise LookupError("account")
    if category_id is not None and await get_category(session, user_id, category_id) is None:
        raise LookupError("category")
    row = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        date=date,
        description=description.strip(),
        amount=amount,
        type=type_,
        source="MANUAL",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_tx(session: AsyncSession, user_id: int, tx_id: int) -> Transaction | None:
    res = await session.execute(select(Transaction).where(Transaction.id == tx_id, Transaction.user_id == user_id))
    return res.scalar_one_or_none()


async def list_txs(session: AsyncSession, user_id: int, f: TxFilters, page: int, per_page: int):
    base = f.apply(select(Transaction).where(Transaction.user_id == user_id))
    total = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    res = await session.execute(
        base.order_by(Transaction.date.desc(), Transaction.id.desc()).offset((page - 1) * per_page).limit(per_page)
    )
    return list(res.scalars().all()), total


async def export_txs(session: AsyncSession, user_id: int, f: TxFilters, limit: int = 10000):
    res = await session.execute(
        f.apply(select(Transaction).where(Transaction.user_id == user_id))
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(limit)
    )
    return list(res.scalars().all())


async def delete_tx(session: AsyncSession, row: Transaction) -> None:
    await session.delete(row)
    await session.commit()
