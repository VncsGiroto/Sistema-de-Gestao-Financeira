from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import http_error
from app.modules.auth.deps import get_current_user
from app.modules.installments import repository as repo
from app.modules.installments.schemas import InstallmentIn, InstallmentOut, InstallmentPatch, ScheduleItem

router = APIRouter(prefix="/api/installments", tags=["installments"])

not_found = lambda: http_error(status.HTTP_404_NOT_FOUND, "Not Found", "Recurso não encontrado")  # noqa: E731


def _out(r) -> InstallmentOut:
    return InstallmentOut(
        id=r.id,
        description=r.description,
        total_amount=r.total_amount,
        num_installments=r.num_installments,
        installment_amount=r.installment_amount,
        first_due_date=r.first_due_date,
        account_id=r.account_id,
    )


@router.get("", response_model=list[InstallmentOut])
async def list_all(session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    return [_out(r) for r in await repo.list_all(session, user.id)]


@router.post("", response_model=InstallmentOut, status_code=status.HTTP_201_CREATED)
async def create(body: InstallmentIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.create(
        session,
        user.id,
        body.description,
        body.total_amount,
        body.num_installments,
        body.first_due_date,
        body.account_id,
    )
    if row is None:
        raise not_found()  # conta de outro usuário
    return _out(row)


@router.get("/{inst_id}", response_model=InstallmentOut)
async def get_one(inst_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_one(session, user.id, inst_id)
    if row is None:
        raise not_found()
    return _out(row)


@router.get("/{inst_id}/schedule", response_model=list[ScheduleItem])
async def get_schedule(inst_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_one(session, user.id, inst_id)
    if row is None:
        raise not_found()
    return [ScheduleItem(**s) for s in repo.build_schedule(row)]


@router.patch("/{inst_id}", response_model=InstallmentOut)
async def patch(
    inst_id: int, body: InstallmentPatch, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    row = await repo.get_one(session, user.id, inst_id)
    if row is None:
        raise not_found()
    data = body.model_dump(exclude_unset=True)
    if "account_id" in data:
        if data["account_id"] is not None and await repo.owned_account(session, user.id, data["account_id"]) is None:
            raise not_found()
        row.account_id = data["account_id"]
    if "description" in data:
        row.description = data["description"]
    await session.commit()
    await session.refresh(row)
    return _out(row)


@router.delete("/{inst_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(inst_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_one(session, user.id, inst_id)
    if row is None:
        raise not_found()
    await repo.delete(session, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
