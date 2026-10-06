from datetime import date as date_t
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import http_error
from app.modules.auth.deps import get_current_user
from app.modules.movements import service as svc
from app.modules.movements.schemas import MovementPage, MovementPageMeta

router = APIRouter(prefix="/api/movements", tags=["movements"])

not_found = lambda: http_error(status.HTTP_404_NOT_FOUND, "Not Found", "Recurso não encontrado")  # noqa: E731
unprocessable = lambda d: http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unprocessable", d)  # noqa: E731


def _filters(
    from_: date_t | None = Query(default=None, alias="from"),
    to: date_t | None = Query(default=None, alias="to"),
    account_id: int | None = None,
    kind: list[str] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> dict:
    return {"from_": from_, "to": to, "account_id": account_id, "kinds": kind or [], "page": page, "per_page": per_page}


@router.get("", response_model=MovementPage)
async def list_movements(
    f: dict = Depends(_filters),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    try:
        data, total = await svc.query_movements(session, user.id, **f)
    except LookupError:
        raise not_found()
    except ValueError as e:
        raise unprocessable(str(e))
    return MovementPage(data=data, meta=MovementPageMeta(page=f["page"], per_page=f["per_page"], total=total))


@router.get("/export/csv")
async def export_csv(
    from_: date_t | None = Query(default=None, alias="from"),
    to: date_t | None = Query(default=None, alias="to"),
    account_id: int | None = None,
    kind: list[str] | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    """CSV na mesma representação da lista (mesmos filtros/fontes/ordenação)."""
    import csv
    import io

    from app.modules.finance import repository as finance_repo
    from app.modules.investments import repository as inv_repo

    try:
        data, _ = await svc.query_movements(
            session, user.id, from_=from_, to=to, account_id=account_id, kinds=kind or [], page=1, per_page=10000
        )
    except LookupError:
        raise not_found()
    except ValueError as e:
        raise unprocessable(str(e))
    accs = {a.id: a.name for a in await finance_repo.list_accounts(session, user.id)}
    assets = {a.id: a.ticker for a in await inv_repo.list_assets(session, user.id)}
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(
        ["id", "date", "kind", "description", "amount", "direction", "cash_impact", "account", "from", "to", "asset"]
    )
    for m in data:
        w.writerow(
            [
                m.id,
                m.date.isoformat(),
                m.kind,
                m.description,
                f"{Decimal(m.amount):.2f}",
                m.direction,
                f"{Decimal(m.cash_impact):.2f}",
                accs.get(m.account_id, "") if m.account_id else "",
                accs.get(m.from_account_id, "") if m.from_account_id else "",
                accs.get(m.to_account_id, "") if m.to_account_id else "",
                assets.get(m.asset_id, "") if m.asset_id else "",
            ]
        )
    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=movements.csv"},
    )
