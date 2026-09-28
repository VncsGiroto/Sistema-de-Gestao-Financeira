from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import http_error
from app.modules.auth.deps import get_current_user
from app.modules.payables import repository as repo
from app.modules.payables.schemas import (
    PayableIn,
    PayableOut,
    PayablePatch,
    PayIn,
    PayOut,
    PayTxOut,
    ScheduleItemOut,
)

router = APIRouter(prefix="/api/payables", tags=["payables"])

not_found = lambda: http_error(status.HTTP_404_NOT_FOUND, "Not Found", "Recurso não encontrado")  # noqa: E731
unprocessable = lambda d: http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unprocessable", d)  # noqa: E731


def _out(r) -> PayableOut:
    return PayableOut(
        id=r.id, description=r.description, kind=r.kind, amount=r.amount,
        periodicity=r.periodicity, due_day=r.due_day, next_due=r.next_due,
        total_amount=r.total_amount, num_installments=r.num_installments,
        installment_amount=r.installment_amount, first_due_date=r.first_due_date,
        paid_ns=r.paid_ns or [], paid_at=r.paid_at,
        account_id=r.account_id, category_id=r.category_id,
    )


@router.get("", response_model=list[PayableOut])
async def list_all(
    kind: str | None = Query(default=None, pattern="^(FIXED|RECURRING|INSTALLMENT|ONE_TIME)$"),
    session: AsyncSession = Depends(get_session), user=Depends(get_current_user),
):
    return [_out(r) for r in await repo.list_all(session, user.id, kind)]


# NOTE: antes de /{payable_id} para não cair no path param
@router.get("/upcoming", response_model=list[PayableOut])
async def upcoming(
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session), user=Depends(get_current_user),
):
    return [_out(r) for r in await repo.upcoming(session, user.id, days, date.today())]


@router.post("", response_model=PayableOut, status_code=status.HTTP_201_CREATED)
async def create(body: PayableIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    try:
        row = await repo.create(
            session, user.id, body.description, body.kind, body.amount,
            body.periodicity, body.due_day, body.next_due, body.total_amount,
            body.num_installments, body.first_due_date, body.account_id,
            body.category_id, date.today(),
        )
    except repo.PayableError as e:
        raise unprocessable(str(e))
    if row is None:
        raise not_found()  # conta/categoria de outro usuário
    return _out(row)


@router.get("/{payable_id}", response_model=PayableOut)
async def get_one(payable_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_one(session, user.id, payable_id)
    if row is None:
        raise not_found()
    return _out(row)


@router.get("/{payable_id}/schedule", response_model=list[ScheduleItemOut])
async def get_schedule(payable_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_one(session, user.id, payable_id)
    if row is None:
        raise not_found()
    try:
        sched = repo.build_schedule(row)
    except repo.PayableError as e:
        raise unprocessable(str(e))
    return [ScheduleItemOut(**s) for s in sched]


@router.patch("/{payable_id}", response_model=PayableOut)
async def patch(payable_id: int, body: PayablePatch, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    from app.modules.finance.models import Account, Category
    from sqlalchemy import select

    row = await repo.get_one(session, user.id, payable_id)
    if row is None:
        raise not_found()
    data = body.model_dump(exclude_unset=True)
    if "account_id" in data:
        if data["account_id"] is not None:
            res = await session.execute(select(Account).where(Account.id == data["account_id"], Account.user_id == user.id))
            if res.scalar_one_or_none() is None:
                raise not_found()
        row.account_id = data["account_id"]
    if "category_id" in data:
        if data["category_id"] is not None:
            res = await session.execute(select(Category).where(Category.id == data["category_id"], Category.user_id == user.id))
            if res.scalar_one_or_none() is None:
                raise not_found()
        row.category_id = data["category_id"]
    if "description" in data:
        row.description = data["description"]
    if "amount" in data:
        if row.kind == "INSTALLMENT":
            raise unprocessable("INSTALLMENT não edita amount (use total via nova conta)")
        row.amount = data["amount"]
    if "next_due" in data:
        if row.kind != "ONE_TIME":
            raise unprocessable("next_due só é editável em ONE_TIME")
        row.next_due = data["next_due"]
    await session.commit()
    await session.refresh(row)
    return _out(row)


@router.post("/{payable_id}/pay", response_model=PayOut)
async def pay(payable_id: int, body: PayIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_one(session, user.id, payable_id)
    if row is None:
        raise not_found()
    try:
        txs = await repo.pay(
            session, user.id, row, body.account_id, body.amount,
            body.date or date.today(), body.category_id, body.ns, body.discount,
        )
    except LookupError:
        raise not_found()
    except repo.PayableError as e:
        raise unprocessable(str(e))
    return PayOut(
        transactions=[PayTxOut(id=t.id, description=t.description, amount=t.amount, date=t.date) for t in txs],
        payable=_out(row),
    )


@router.delete("/{payable_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(payable_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_one(session, user.id, payable_id)
    if row is None:
        raise not_found()
    await repo.delete(session, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
