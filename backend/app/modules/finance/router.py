from datetime import date as date_t
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import http_error
from app.modules.auth.deps import get_current_user
from app.modules.finance import repository as repo
from app.modules.finance.schemas import (
    AccountIn,
    AccountOut,
    AccountPatch,
    CategoryIn,
    CategoryOut,
    CategoryPatch,
    PageMeta,
    TxIn,
    TxOut,
    TxPage,
    TxPatch,
)

accounts = APIRouter(prefix="/api/accounts", tags=["accounts"])
categories = APIRouter(prefix="/api/categories", tags=["categories"])
transactions = APIRouter(prefix="/api/transactions", tags=["transactions"])

not_found = lambda: http_error(status.HTTP_404_NOT_FOUND, "Not Found", "Recurso não encontrado")  # noqa: E731


def _account_out(row) -> AccountOut:
    return AccountOut(
        id=row.id, name=row.name, bank=row.bank,
        account_type=row.account_type, initial_balance=row.initial_balance,
    )


@accounts.get("", response_model=list[AccountOut])
async def list_accounts(session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    return [_account_out(r) for r in await repo.list_accounts(session, user.id)]


@accounts.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(body: AccountIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.create_account(session, user.id, **body.model_dump())
    return _account_out(row)


@accounts.get("/{account_id}", response_model=AccountOut)
async def get_account(account_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_account(session, user.id, account_id)
    if row is None:
        raise not_found()  # 404 também para recurso de outro usuário (não vaza existência)
    return _account_out(row)


@accounts.patch("/{account_id}", response_model=AccountOut)
async def patch_account(account_id: int, body: AccountPatch, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_account(session, user.id, account_id)
    if row is None:
        raise not_found()
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return _account_out(row)


@accounts.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_account(session, user.id, account_id)
    if row is None:
        raise not_found()
    try:
        await repo.delete_account(session, row)
    except IntegrityError:
        await session.rollback()
        raise http_error(status.HTTP_409_CONFLICT, "Conflict", "Conta possui movimentações e não pode ser excluída")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@categories.get("", response_model=list[CategoryOut])
async def list_categories(
    type: str | None = None, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    if type and type not in ("INCOME", "EXPENSE"):
        raise http_error(status.HTTP_400_BAD_REQUEST, "Bad Request", "type inválido")
    rows = await repo.list_categories(session, user.id, type)
    return [CategoryOut(id=r.id, name=r.name, type=r.type) for r in rows]


@categories.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(body: CategoryIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.create_category(session, user.id, body.name, body.type)
    return CategoryOut(id=row.id, name=row.name, type=row.type)


@categories.get("/{category_id}", response_model=CategoryOut)
async def get_category(category_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_category(session, user.id, category_id)
    if row is None:
        raise not_found()
    return CategoryOut(id=row.id, name=row.name, type=row.type)


@categories.patch("/{category_id}", response_model=CategoryOut)
async def patch_category(category_id: int, body: CategoryPatch, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_category(session, user.id, category_id)
    if row is None:
        raise not_found()
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return CategoryOut(id=row.id, name=row.name, type=row.type)


@categories.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_category(session, user.id, category_id)
    if row is None:
        raise not_found()
    await repo.delete_category(session, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _tx_out(row) -> TxOut:
    return TxOut(
        id=row.id, account_id=row.account_id, category_id=row.category_id, date=row.date,
        description=row.description, amount=row.amount, type=row.type, source=row.source,
    )


def _filters(
    from_: date_t | None = Query(default=None, alias="from"),
    to: date_t | None = Query(default=None, alias="to"),
    account_id: int | None = None,
    category_id: int | None = None,
    type: str | None = Query(default=None, pattern="^(INCOME|EXPENSE)$"),
    source: str | None = Query(default=None, pattern="^(MANUAL|OFX|IMPORT)$"),
    q: str | None = Query(default=None, max_length=200),
    min: Decimal | None = Query(default=None, alias="min"),
    max: Decimal | None = Query(default=None, alias="max"),
) -> repo.TxFilters:
    return repo.TxFilters(from_, to, account_id, category_id, type, source, q, min, max)


@transactions.get("", response_model=TxPage)
async def list_txs(
    f: repo.TxFilters = Depends(_filters),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    rows, total = await repo.list_txs(session, user.id, f, page, per_page)
    return TxPage(data=[_tx_out(r) for r in rows], meta=PageMeta(page=page, per_page=per_page, total=total))


@transactions.post("", response_model=TxOut, status_code=status.HTTP_201_CREATED)
async def create_tx(body: TxIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    try:
        row = await repo.create_tx(
            session, user.id, body.account_id, body.category_id,
            body.date, body.description, body.amount, body.type,
        )
    except LookupError:
        raise not_found()
    return _tx_out(row)


@transactions.get("/{tx_id}", response_model=TxOut)
async def get_tx(tx_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_tx(session, user.id, tx_id)
    if row is None:
        raise not_found()
    return _tx_out(row)


@transactions.patch("/{tx_id}", response_model=TxOut)
async def patch_tx(tx_id: int, body: TxPatch, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_tx(session, user.id, tx_id)
    if row is None:
        raise not_found()
    data = body.model_dump(exclude_unset=True)
    if "account_id" in data and await repo.get_account(session, user.id, data["account_id"]) is None:
        raise not_found()
    if "category_id" in data and data["category_id"] is not None and await repo.get_category(session, user.id, data["category_id"]) is None:
        raise not_found()
    for k, v in data.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return _tx_out(row)


@transactions.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tx(tx_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_tx(session, user.id, tx_id)
    if row is None:
        raise not_found()
    await repo.delete_tx(session, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@transactions.get("/export/csv")
async def export_csv(
    f: repo.TxFilters = Depends(_filters),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    import csv
    import io

    rows = await repo.export_txs(session, user.id, f)
    accs = {a.id: a.name for a in await repo.list_accounts(session, user.id)}
    cats = {c.id: c.name for c in await repo.list_categories(session, user.id)}
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["id", "date", "description", "amount", "type", "account", "category", "source"])
    for r in rows:
        w.writerow([r.id, r.date.isoformat(), r.description, f"{r.amount:.2f}", r.type, accs.get(r.account_id, ""), cats.get(r.category_id, "") if r.category_id else "", r.source])
    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )
