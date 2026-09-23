"""Agenda unificada de compromissos futuros (somente leitura)."""

from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bills import repository as bills_repo
from app.modules.installments import repository as inst_repo


async def get_commitments(session: AsyncSession, user_id: int, horizon_days: int = 60) -> dict:
    limit = date.today().fromordinal(date.today().toordinal() + horizon_days)
    items: list[dict] = []

    for b in await bills_repo.list_all(session, user_id):
        if b.next_due and b.next_due <= limit:
            items.append(
                {
                    "kind": "bill",
                    "description": b.description,
                    "due_date": b.next_due,
                    "amount": b.amount,
                    "ref_id": b.id,
                }
            )
    for inst in await inst_repo.list_all(session, user_id):
        for p in inst_repo.build_schedule(inst):
            if p["due_date"] <= limit:
                items.append(
                    {
                        "kind": "installment",
                        "description": f"{inst.description} ({p['n']}/{inst.num_installments})",
                        "due_date": p["due_date"],
                        "amount": p["amount"],
                        "ref_id": inst.id,
                    }
                )
    items.sort(key=lambda i: (i["due_date"], i["description"]))
    total = sum((i["amount"] for i in items), Decimal("0"))
    return {"total": total, "items": items}
