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
    BulkCategoryIn,
    BulkCategoryOut,
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
unprocessable = lambda d: http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unprocessable", d)  # noqa: E731


def _account_out(row, summary: dict | None = None) -> AccountOut:
    summary = summary or {}
    income = summary.get("income", Decimal("0"))
    expense = summary.get("expense", Decimal("0"))
    ledger_in = summary.get("ledger_in", Decimal("0"))
    ledger_out = summary.get("ledger_out", Decimal("0"))
    return AccountOut(
        id=row.id,
        name=row.name,
        bank=row.bank,
        account_type=row.account_type,
        initial_balance=row.initial_balance,
        current_balance=row.initial_balance + income - expense + ledger_in - ledger_out,
        total_income=income,
        total_expense=expense,
        last_transaction_date=summary.get("last_date"),
    )


@accounts.get("", response_model=list[AccountOut])
async def list_accounts(session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    sums = await repo.account_summaries(session, user.id, date_t.today())
    return [_account_out(r, sums.get(r.id)) for r in await repo.list_accounts(session, user.id)]


@accounts.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(body: AccountIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.create_account(session, user.id, **body.model_dump())
    # O saldo inicial entra no caixa de todas as datas: reconstrói a série inteira.
    from app.modules.investments import portfolio as pf

    await pf.rebuild_snapshots(session, user.id)
    await session.commit()
    sums = await repo.account_summaries(session, user.id, date_t.today())
    return _account_out(row, sums.get(row.id))


@accounts.get("/{account_id}", response_model=AccountOut)
async def get_account(account_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_account(session, user.id, account_id)
    if row is None:
        raise not_found()  # 404 também para recurso de outro usuário (não vaza existência)
    sums = await repo.account_summaries(session, user.id, date_t.today())
    return _account_out(row, sums.get(row.id))


@accounts.patch("/{account_id}", response_model=AccountOut)
async def patch_account(
    account_id: int, body: AccountPatch, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    row = await repo.get_account(session, user.id, account_id)
    if row is None:
        raise not_found()
    data = body.model_dump(exclude_unset=True)
    if "account_type" in data and data["account_type"] != row.account_type:
        # Trocar o tipo com vínculos reclassificaria a carteira e os fluxos históricos.
        if await repo.has_investment_links(session, user.id, account_id):
            raise unprocessable("Conta com investimentos ou transferências não pode trocar de tipo")
    for k, v in data.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    # Saldo inicial/tipo mudam o caixa histórico: reconstrói a série inteira.
    from app.modules.investments import portfolio as pf

    await pf.rebuild_snapshots(session, user.id)
    await session.commit()
    sums = await repo.account_summaries(session, user.id, date_t.today())
    return _account_out(row, sums.get(row.id))


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
    from app.modules.investments import portfolio as pf

    await pf.rebuild_snapshots(session, user.id)
    await session.commit()
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
async def create_category(
    body: CategoryIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    row = await repo.create_category(session, user.id, body.name, body.type)
    return CategoryOut(id=row.id, name=row.name, type=row.type)


@categories.get("/{category_id}", response_model=CategoryOut)
async def get_category(category_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_category(session, user.id, category_id)
    if row is None:
        raise not_found()
    return CategoryOut(id=row.id, name=row.name, type=row.type)


@categories.patch("/{category_id}", response_model=CategoryOut)
async def patch_category(
    category_id: int, body: CategoryPatch, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    row = await repo.get_category(session, user.id, category_id)
    if row is None:
        raise not_found()
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return CategoryOut(id=row.id, name=row.name, type=row.type)


@categories.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    row = await repo.get_category(session, user.id, category_id)
    if row is None:
        raise not_found()
    await repo.delete_category(session, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _tx_out(row) -> TxOut:
    return TxOut(
        id=row.id,
        account_id=row.account_id,
        category_id=row.category_id,
        date=row.date,
        description=row.description,
        amount=row.amount,
        type=row.type,
        source=row.source,
        payable_id=row.payable_id,
    )


def _filters(
    from_: date_t | None = Query(default=None, alias="from"),
    to: date_t | None = Query(default=None, alias="to"),
    account_id: int | None = None,
    category_id: int | None = None,
    type: str | None = Query(default=None, pattern="^(INCOME|EXPENSE)$"),
    source: str | None = Query(default=None, pattern="^(MANUAL|OFX|IMPORT|PAYABLE)$"),
    payable_id: int | None = None,
    import_id: int | None = None,
    q: str | None = Query(default=None, max_length=200),
    min: Decimal | None = Query(default=None, alias="min"),
    max: Decimal | None = Query(default=None, alias="max"),
) -> repo.TxFilters:
    return repo.TxFilters(from_, to, account_id, category_id, type, source, payable_id, import_id, q, min, max)


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
            session,
            user.id,
            body.account_id,
            body.category_id,
            body.date,
            body.description,
            body.amount,
            body.type,
        )
    except LookupError:
        raise not_found()
    except repo.CategoryMismatch as e:
        raise unprocessable(str(e))
    from app.modules.investments import portfolio as pf

    await pf.record_snapshot(session, user.id, row.date)
    return _tx_out(row)


@transactions.post("/categorize", response_model=BulkCategoryOut)
async def bulk_categorize(
    body: BulkCategoryIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    try:
        out = await repo.bulk_set_category(session, user.id, body.ids, body.category_id)
    except LookupError:
        raise not_found()
    return BulkCategoryOut(**out)


@transactions.get("/{tx_id}", response_model=TxOut)
async def get_tx(tx_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_tx(session, user.id, tx_id)
    if row is None:
        raise not_found()
    return _tx_out(row)


@transactions.patch("/{tx_id}", response_model=TxOut)
async def patch_tx(
    tx_id: int, body: TxPatch, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    row = await repo.get_tx(session, user.id, tx_id)
    if row is None:
        raise not_found()
    if await repo.is_investment_linked(session, user.id, tx_id):
        raise unprocessable("Transação gerada por operação de investimento; edite ou exclua pela operação")
    data = body.model_dump(exclude_unset=True)
    old_date = row.date
    if "account_id" in data and await repo.get_account(session, user.id, data["account_id"]) is None:
        raise not_found()
    # valida o estado final (tipo/categoria após o patch, não só o que foi enviado)
    final_cat = data.get("category_id", row.category_id)
    final_type = data.get("type", row.type)
    try:
        await repo.ensure_category_compat(session, user.id, final_cat, final_type)
    except LookupError:
        raise not_found()
    except repo.CategoryMismatch as e:
        raise unprocessable(str(e))
    for k, v in data.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    from app.modules.investments import portfolio as pf

    new_date = data.get("date") or old_date
    await pf.record_snapshot(session, user.id, min(old_date, new_date))
    return _tx_out(row)


@transactions.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tx(tx_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_tx(session, user.id, tx_id)
    if row is None:
        raise not_found()
    if await repo.is_investment_linked(session, user.id, tx_id):
        raise unprocessable("Transação gerada por operação de investimento; edite ou exclua pela operação")
    tx_date = row.date
    await repo.delete_tx(session, row)
    from app.modules.investments import portfolio as pf

    await pf.record_snapshot(session, user.id, tx_date)
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
        w.writerow(
            [
                r.id,
                r.date.isoformat(),
                r.description,
                f"{r.amount:.2f}",
                r.type,
                accs.get(r.account_id, ""),
                cats.get(r.category_id, "") if r.category_id else "",
                r.source,
            ]
        )
    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )
