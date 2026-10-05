"""Agregações do dashboard. Puro em cima de linhas já carregadas, exceto queries de escopo."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance.models import Account, Category, Transaction


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def month_range(from_: date | None, to: date | None) -> tuple[date, date]:
    """Sem período: últimos 6 meses cheios até o mês atual."""
    if from_ and to:
        return _month_start(from_), to
    if from_:
        return _month_start(from_), date.today()
    today = date.today()
    if to:
        return _add_months(_month_start(to), -5), to
    return _add_months(_month_start(today), -5), today


def _months_between(start: date, end: date) -> list[str]:
    out, cur = [], _month_start(start)
    while cur <= end:
        out.append(cur.strftime("%Y-%m"))
        cur = _add_months(cur, 1)
    return out


async def get_dashboard(
    session: AsyncSession,
    user_id: int,
    from_: date | None = None,
    to: date | None = None,
    account_id: int | None = None,
) -> dict:
    start_m, end = month_range(from_, to)

    acc_q = select(Account).where(Account.user_id == user_id)
    if account_id:
        acc_q = acc_q.where(Account.id == account_id)
    accounts = list((await session.execute(acc_q)).scalars().all())
    if account_id and not accounts:
        raise LookupError("account")
    initial = sum((a.initial_balance for a in accounts), Decimal("0"))

    tx_q = select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.date >= start_m,
        Transaction.date <= end,
    )
    if account_id:
        tx_q = tx_q.where(Transaction.account_id == account_id)
    txs = list((await session.execute(tx_q)).scalars().all())

    # Saldo cumulativo até `end` (todos os lançamentos, sem corte de janela):
    # evita que movimentações antigas "sumam" do saldo. Só income/expense/
    # evolution respeitam a janela.
    cum_q = select(Transaction.type, Transaction.amount).where(
        Transaction.user_id == user_id,
        Transaction.date <= end,
    )
    if account_id:
        cum_q = cum_q.where(Transaction.account_id == account_id)
    cum_income = cum_expense = Decimal("0")
    for ttype, amount in (await session.execute(cum_q)).all():
        if ttype == "INCOME":
            cum_income += amount
        else:
            cum_expense += amount

    cats = {
        c.id: c.name
        for c in (await session.execute(select(Category).where(Category.user_id == user_id))).scalars().all()
    }

    income = Decimal("0")
    expense = Decimal("0")
    by_inc: dict[str, Decimal] = {}
    by_exp: dict[str, Decimal] = {}
    evo: dict[str, dict[str, Decimal]] = {}
    for m in _months_between(start_m, end):
        evo[m] = {"income": Decimal("0"), "expense": Decimal("0")}
    for t in txs:
        v = t.amount
        m = t.date.strftime("%Y-%m")
        name: str = cats.get(t.category_id, "Sem categoria") if t.category_id else "Sem categoria"
        if t.type == "INCOME":
            income += v
            by_inc[name] = by_inc.get(name, Decimal("0")) + v
            evo.setdefault(m, {"income": Decimal("0"), "expense": Decimal("0")})["income"] += v
        else:
            expense += v
            by_exp[name] = by_exp.get(name, Decimal("0")) + v
            evo.setdefault(m, {"income": Decimal("0"), "expense": Decimal("0")})["expense"] += v

    # Mês anterior ao início da janela (base de comparação) + lançamentos sem categoria.
    pm_start = _add_months(start_m, -1)
    pm_end = start_m - timedelta(days=1)
    pm_q = select(Transaction.type, Transaction.amount).where(
        Transaction.user_id == user_id,
        Transaction.date >= pm_start,
        Transaction.date <= pm_end,
    )
    if account_id:
        pm_q = pm_q.where(Transaction.account_id == account_id)
    pm_income = pm_expense = Decimal("0")
    for ttype, amount in (await session.execute(pm_q)).all():
        if ttype == "INCOME":
            pm_income += amount
        else:
            pm_expense += amount
    uncat_q = select(Transaction.id).where(
        Transaction.user_id == user_id,
        Transaction.date >= start_m,
        Transaction.date <= end,
        Transaction.category_id.is_(None),
    )
    if account_id:
        uncat_q = uncat_q.where(Transaction.account_id == account_id)
    uncategorized = len((await session.execute(uncat_q)).all())

    return {
        "balance": initial + cum_income - cum_expense,
        "income": {"total": income, "by_category": [{"name": k, "total": v} for k, v in sorted(by_inc.items())]},
        "expense": {"total": expense, "by_category": [{"name": k, "total": v} for k, v in sorted(by_exp.items())]},
        "evolution": [{"month": m, "income": evo[m]["income"], "expense": evo[m]["expense"]} for m in sorted(evo)],
        "prev_month": {"month": pm_start.strftime("%Y-%m"), "income": pm_income, "expense": pm_expense},
        "uncategorized": uncategorized,
    }
