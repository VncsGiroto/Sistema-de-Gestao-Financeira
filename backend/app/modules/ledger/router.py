from datetime import date

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import http_error
from app.modules.auth.deps import get_current_user
from app.modules.ledger import repository as repo
from app.modules.ledger.schemas import MovementOut, TransferIn

router = APIRouter(prefix="/api/transfers", tags=["transfers"])

not_found = lambda: http_error(status.HTTP_404_NOT_FOUND, "Not Found", "Recurso não encontrado")  # noqa: E731
unprocessable = lambda d: http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unprocessable", d)  # noqa: E731


def _out(row) -> MovementOut:
    return MovementOut(
        id=row.id,
        from_account_id=row.from_account_id,
        to_account_id=row.to_account_id,
        kind=row.kind,
        amount=row.amount,
        date=row.date,
        description=row.description,
        op_id=row.op_id,
        asset_id=row.asset_id,
    )


@router.get("", response_model=list[MovementOut])
async def list_transfers(
    account_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    from app.modules.finance import repository as finance_repo

    if account_id is not None and await finance_repo.get_account(session, user.id, account_id) is None:
        raise not_found()
    return [_out(r) for r in await repo.list_movements(session, user.id, account_id)]


@router.post("", response_model=MovementOut, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    body: TransferIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    try:
        row = await repo.create_transfer(
            session,
            user.id,
            body.from_account_id,
            body.to_account_id,
            body.amount,
            body.date or date.today(),
            body.description,
        )
    except LookupError:
        raise not_found()
    except repo.LedgerError as e:
        raise unprocessable(str(e))
    return _out(row)


@router.delete("/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transfer(
    movement_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    row = await repo.get_movement(session, user.id, movement_id)
    if row is None:
        raise not_found()
    try:
        await repo.delete_movement(session, row)
    except repo.LedgerError as e:
        raise unprocessable(str(e))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
