import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.errors import http_error
from app.modules.auth.deps import get_current_user, rate_limit
from app.modules.finance import repository as finance_repo
from app.modules.imports import repository as repo
from app.modules.imports import service
from app.modules.imports.models import Import
from app.modules.imports.schemas import CommitOut, ImportItemOut, ImportOut, ReviewIn

router = APIRouter(prefix="/api/imports", tags=["imports"])

not_found = lambda: http_error(status.HTTP_404_NOT_FOUND, "Not Found", "Recurso não encontrado")  # noqa: E731


def _out(imp: Import) -> ImportOut:
    return ImportOut(
        id=imp.id, account_id=imp.account_id, source=imp.source, file_name=imp.file_name,
        status=imp.status, total_rows=imp.total_rows, imported_rows=imp.imported_rows,
        duplicate_rows=imp.duplicate_rows, error=imp.error,
        created_at=imp.created_at, processed_at=imp.processed_at,
    )


@router.post("/ofx", status_code=status.HTTP_202_ACCEPTED)
async def upload_ofx(
    request: Request,
    background: BackgroundTasks,
    account_id: int = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    await rate_limit(request, "ofx", 10, window_s=3600)
    name = (file.filename or "").lower()
    if not name.endswith((".ofx", ".qfx")):
        raise http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unprocessable", "Envie um arquivo .ofx ou .qfx")
    if await finance_repo.get_account(session, user.id, account_id) is None:
        raise not_found()
    raw = await file.read()
    if not raw:
        raise http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unprocessable", "Arquivo vazio")
    if len(raw) > settings.ofx_max_bytes:
        raise http_error(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Payload Too Large", "Máximo de 10MB")
    os.makedirs(settings.ofx_dir, exist_ok=True)
    path = os.path.join(settings.ofx_dir, f"{user.id}_{uuid.uuid4().hex}.ofx")
    with open(path, "wb") as fh:
        fh.write(raw)
    imp = Import(
        user_id=user.id, account_id=account_id, source="OFX",
        file_name=file.filename or "arquivo.ofx", file_path=path,
        status="RECEIVED", created_at=datetime.now(UTC),
    )
    session.add(imp)
    await session.commit()
    await session.refresh(imp)
    background.add_task(service.process_import, imp.id)
    return {"import_id": imp.id, "status": imp.status}


@router.get("", response_model=list[ImportOut])
async def list_imports(session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    return [_out(i) for i in await repo.list_imports(session, user.id)]


@router.get("/{import_id}", response_model=ImportOut)
async def get_import(import_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    imp = await repo.get_import(session, user.id, import_id)
    if imp is None:
        raise not_found()
    counts = await repo.count_items(session, import_id)
    imp.total_rows = sum(counts.values()) or imp.total_rows
    return _out(imp)


@router.get("/{import_id}/items", response_model=list[ImportItemOut])
async def list_items(
    import_id: int, verdict: str | None = None,
    session: AsyncSession = Depends(get_session), user=Depends(get_current_user),
):
    if verdict and verdict not in ("NEW", "EXACT_DUPLICATE", "FUZZY_CANDIDATE", "INVALID"):
        raise http_error(status.HTTP_400_BAD_REQUEST, "Bad Request", "verdict inválido")
    rows = await repo.list_items(session, user.id, import_id, verdict)
    if rows is None:
        raise not_found()
    return [ImportItemOut(id=r.id, row_no=r.row_no, verdict=r.verdict, payload=r.payload, matched_transaction_id=r.matched_transaction_id) for r in rows]


@router.post("/{import_id}/review")
async def review_import(
    import_id: int, body: ReviewIn,
    session: AsyncSession = Depends(get_session), user=Depends(get_current_user),
):
    try:
        n = await service.review(session, user.id, import_id, [d.model_dump() for d in body.decisions])
    except LookupError:
        raise not_found()
    except service.ReviewError as e:
        raise http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unprocessable", str(e))
    return {"decided": n}


@router.post("/{import_id}/commit", response_model=CommitOut)
async def commit_import(
    import_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user),
):
    try:
        out = await service.commit(session, user.id, import_id)
    except LookupError:
        raise not_found()
    except service.CommitBlocked as e:
        raise http_error(status.HTTP_409_CONFLICT, "Conflict", str(e))
    return CommitOut(**out)
