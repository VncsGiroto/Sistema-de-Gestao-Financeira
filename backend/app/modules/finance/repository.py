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


async def account_summaries(session: AsyncSession, user_id: int) -> dict[int, dict]:
    """Totais por conta (1 GROUP BY): {account_id: {income, expense, last_date}}."""
    out: dict[int, dict] = {}
    sums = await session.execute(
        select(Transaction.account_id, Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.user_id == user_id)
        .group_by(Transaction.account_id, Transaction.type)
    )
    for account_id, ttype, total in sums.all():
        d = out.setdefault(account_id, {"income": Decimal("0"), "expense": Decimal("0"), "last_date": None})
        d["income" if ttype == "INCOME" else "expense"] = total or Decimal("0")
    lasts = await session.execute(
        select(Transaction.account_id, func.max(Transaction.date))
        .where(Transaction.user_id == user_id)
        .group_by(Transaction.account_id)
    )
    for account_id, last_date in lasts.all():
        out.setdefault(account_id, {"income": Decimal("0"), "expense": Decimal("0"), "last_date": None})[
            "last_date"
        ] = last_date
    return out


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


class CategoryMismatch(ValueError):
    """Categoria existe mas é de tipo (INCOME/EXPENSE) incompatível com a transação."""


async def ensure_category_compat(session: AsyncSession, user_id: int, category_id: int | None, tx_type: str) -> None:
    """Categoria inexistente/de outro usuário → LookupError; tipo divergente → CategoryMismatch."""
    if category_id is None:
        return
    cat = await get_category(session, user_id, category_id)
    if cat is None:
        raise LookupError("category")
    if cat.type != tx_type:
        raise CategoryMismatch(f"Categoria '{cat.name}' é {cat.type}, incompatível com transação {tx_type}")


class TxFilters:
    def __init__(
        self,
        from_: date_t | None = None,
        to: date_t | None = None,
        account_id: int | None = None,
        category_id: int | None = None,
        type_: str | None = None,
        source: str | None = None,
        payable_id: int | None = None,
        import_id: int | None = None,
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
        self.payable_id = payable_id
        self.import_id = import_id
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
        if self.payable_id:
            q = q.where(Transaction.payable_id == self.payable_id)
        if self.import_id:
            q = q.where(Transaction.import_id == self.import_id)
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
    await ensure_category_compat(session, user_id, category_id, type_)
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


async def bulk_set_category(session: AsyncSession, user_id: int, ids: list[int], category_id: int) -> dict[str, int]:
    """Aplica a categoria aos lançamentos compatíveis; incompatíveis/inexistentes são contados e pulados."""
    cat = await get_category(session, user_id, category_id)
    if cat is None:
        raise LookupError("category")
    updated = skipped_type = skipped_missing = 0
    for tid in ids:
        row = await get_tx(session, user_id, tid)
        if row is None:
            skipped_missing += 1
            continue
        if row.type != cat.type:
            skipped_type += 1
            continue
        row.category_id = cat.id
        updated += 1
    await session.commit()
    return {"updated": updated, "skipped_type": skipped_type, "skipped_missing": skipped_missing}


async def delete_tx(session: AsyncSession, row: Transaction) -> None:
    await session.delete(row)
    await session.commit()
