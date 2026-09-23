from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import http_error
from app.modules.auth.audit_models import AuditLog
from app.modules.auth.deps import get_current_user
from app.modules.bills import repository as repo
from app.modules.bills.due_dates import next_due_date
from app.modules.bills.models import RecurringBill
from app.modules.bills.schemas import BillIn, BillOut, BillPatch

router = APIRouter(prefix="/api/bills", tags=["bills"])

not_found = lambda: http_error(status.HTTP_404_NOT_FOUND, "Not Found", "Recurso não encontrado")  # noqa: E731
unprocessable = lambda detail: http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unprocessable", detail)  # noqa: E731


def _out(r: RecurringBill) -> BillOut:
    return BillOut(
        id=r.id,
        description=r.description,
        amount=r.amount,
        kind=r.kind,
        periodicity=r.periodicity,
        due_day=r.due_day,
        next_due=r.next_due,
    )


@router.get("", response_model=list[BillOut])
async def list_all(session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    return [_out(r) for r in await repo.list_all(session, user.id)]


# NOTE: antes de /{bill_id} para o "upcoming" não cair no path param
@router.get("/upcoming", response_model=list[BillOut])
async def list_upcoming(days: int = 30, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    return [_out(r) for r in await repo.upcoming(session, user.id, days)]


@router.post("", response_model=BillOut, status_code=status.HTTP_201_CREATED)
async def create(body: BillIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    if body.kind == "ONE_TIME":
        if body.periodicity is not None:
            raise unprocessable("ONE_TIME não usa periodicity")
        if body.next_due is None:
            raise unprocessable("ONE_TIME exige next_due")
        due = body.next_due
    else:
        if body.periodicity is None or body.due_day is None:
            raise unprocessable("Contas recorrentes exigem periodicity e due_day")
        try:
            due = next_due_date(body.kind, body.periodicity, body.due_day, date.today())
        except ValueError as e:
            raise unprocessable(str(e))
    row = await repo.create(
        session,
        RecurringBill(
            user_id=user.id,
            description=body.description.strip(),
            amount=body.amount,
            kind=body.kind,
            periodicity=body.periodicity,
            due_day=body.due_day,
            next_due=due,
        ),
    )
    return _out(row)


@router.get("/{bill_id}", response_model=BillOut)
async def get_one(bill_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_one(session, user.id, bill_id)
    if row is None:
        raise not_found()
    return _out(row)


@router.patch("/{bill_id}", response_model=BillOut)
async def patch(
    bill_id: int, body: BillPatch, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    row = await repo.get_one(session, user.id, bill_id)
    if row is None:
        raise not_found()
    data = body.model_dump(exclude_unset=True)
    old_amount = row.amount if "amount" in data else None
    for k, v in data.items():
        setattr(row, k, v)
    if old_amount is not None and Decimal(str(old_amount)) != Decimal(str(row.amount)):
        session.add(
            AuditLog(
                user_id=user.id,
                action="bill.amount_changed",
                entity="recurring_bills",
                entity_id=row.id,
                meta={"old": str(old_amount), "new": str(row.amount)},
                created_at=datetime.now(UTC),
            )
        )
    await session.commit()
    await session.refresh(row)
    return _out(row)


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(bill_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_one(session, user.id, bill_id)
    if row is None:
        raise not_found()
    await repo.delete(session, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
