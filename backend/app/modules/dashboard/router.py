from datetime import date as date_t

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import http_error
from app.modules.auth.deps import get_current_user
from app.modules.dashboard import commitments as commitments_svc
from app.modules.dashboard import service
from app.modules.dashboard.commitments_schemas import CommitmentsOut
from app.modules.dashboard.schemas import DashboardOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

not_found = lambda: http_error(status.HTTP_404_NOT_FOUND, "Not Found", "Recurso não encontrado")  # noqa: E731


@router.get("", response_model=DashboardOut)
async def dashboard(
    from_: date_t | None = Query(default=None, alias="from"),
    to: date_t | None = Query(default=None, alias="to"),
    account_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    if from_ and to and from_ > to:
        raise http_error(status.HTTP_400_BAD_REQUEST, "Bad Request", "from maior que to")
    try:
        out = await service.get_dashboard(session, user.id, from_, to, account_id)
    except LookupError:
        raise not_found()
    return DashboardOut(**out)


@router.get("/commitments", response_model=CommitmentsOut)
async def commitments(
    horizon_days: int = Query(default=60, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    out = await commitments_svc.get_commitments(session, user.id, horizon_days)
    return CommitmentsOut(**out)
