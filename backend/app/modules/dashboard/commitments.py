"""Agenda unificada de compromissos futuros (somente leitura, sobre payables)."""

from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payables import repository as pay_repo


async def get_commitments(session: AsyncSession, user_id: int, horizon_days: int = 60) -> dict:
    from datetime import timedelta

    limit = date.today() + timedelta(days=horizon_days)
    items: list[dict] = []

    for p in await pay_repo.list_all(session, user_id):
        if p.kind == "INSTALLMENT":
            for s in pay_repo.build_schedule(p):
                if not s["paid"] and s["due_date"] <= limit:
                    items.append(
                        {
                            "kind": "installment",
                            "description": f"{p.description} ({s['n']}/{p.num_installments})",
                            "due_date": s["due_date"],
                            "amount": s["amount"],
                            "ref_id": p.id,
                        }
                    )
        elif p.kind == "ONE_TIME" and p.paid_at is not None:
            continue
        elif p.next_due and p.next_due <= limit:
            items.append(
                {
                    "kind": "bill",
                    "description": p.description,
                    "due_date": p.next_due,
                    "amount": p.amount,
                    "ref_id": p.id,
                }
            )
    items.sort(key=lambda i: (i["due_date"], i["description"]))
    total = sum((i["amount"] for i in items), Decimal("0"))
    return {"total": total, "items": items}
