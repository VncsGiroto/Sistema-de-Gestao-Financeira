"""Agenda unificada de compromissos futuros (somente leitura, sobre payables)."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payables import repository as pay_repo
from app.modules.payables.due_dates import next_due_date


def _bill_occurrences(p, limit: date) -> list[tuple[date, Decimal, str]]:
    """Expande FIXED/RECURRING em todas as ocorrências até o limite (a partir de next_due)."""
    if not p.next_due or p.next_due > limit:
        return []
    out = [(p.next_due, p.amount, p.description)]
    occ = p.next_due
    for _ in range(1000):  # trava de segurança contra configuração degenerada
        try:
            occ = next_due_date(p.kind, p.periodicity, p.due_day, occ + timedelta(days=1))
        except ValueError:
            break
        if occ > limit:
            break
        out.append((occ, p.amount, f"{p.description} ({occ:%m/%Y})"))
    return out


async def get_commitments(
    session: AsyncSession, user_id: int, horizon_days: int = 60, account_id: int | None = None
) -> dict:
    """Com `account_id`: só compromissos vinculados; sem vínculo entram em
    `unassigned_total` (projeção parcial) em vez de contaminar o saldo da conta."""
    limit = date.today() + timedelta(days=horizon_days)
    items: list[dict] = []
    unassigned = Decimal("0")

    for p in await pay_repo.list_all(session, user_id):
        if p.kind == "INSTALLMENT":
            occs = [
                (s["due_date"], s["amount"], f"{p.description} ({s['n']}/{p.num_installments})")
                for s in pay_repo.build_schedule(p)
                if not s["paid"] and s["due_date"] <= limit
            ]
        elif p.kind == "ONE_TIME":
            if p.paid_at is not None or not p.next_due or p.next_due > limit:
                continue
            occs = [(p.next_due, p.amount, p.description)]
        else:
            occs = _bill_occurrences(p, limit)
        if account_id is not None and p.account_id is None:
            unassigned += sum((a for _, a, _ in occs), Decimal("0"))
            continue
        if account_id is not None and p.account_id != account_id:
            continue
        items.extend(
            {
                "kind": "installment" if p.kind == "INSTALLMENT" else "bill",
                "description": d,
                "due_date": dt,
                "amount": a,
                "ref_id": p.id,
                "account_id": p.account_id,
            }
            for dt, a, d in occs
        )
    items.sort(key=lambda i: (i["due_date"], i["description"]))
    total = sum((i["amount"] for i in items), Decimal("0"))
    return {"total": total, "items": items, "unassigned_total": unassigned}
