from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import http_error
from app.modules.auth.deps import get_current_user
from app.modules.investments import repository as repo
from app.modules.investments.schemas import (
    AssetIn,
    AssetOut,
    AssetPatch,
    OpIn,
    OpOut,
    PositionOut,
    PriceIn,
    PriceOut,
    ReturnsOut,
)

router = APIRouter(prefix="/api/assets", tags=["assets"])

not_found = lambda: http_error(status.HTTP_404_NOT_FOUND, "Not Found", "Recurso não encontrado")  # noqa: E731
unprocessable = lambda d: http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unprocessable", d)  # noqa: E731


def _asset_out(r) -> AssetOut:
    return AssetOut(
        id=r.id,
        ticker=r.ticker,
        name=r.name,
        asset_class=r.asset_class,
        subtype=r.subtype,
        custodian=r.custodian,
        currency=r.currency,
        category_id=r.category_id,
        rate_type=r.rate_type,
        rate=r.rate,
        maturity_date=r.maturity_date,
    )


def _op_out(r) -> OpOut:
    return OpOut(
        id=r.id,
        asset_id=r.asset_id,
        kind=r.kind,
        date=r.date,
        quantity=r.quantity,
        price=r.price,
        fees=r.fees,
        amount=r.amount,
        transaction_id=r.transaction_id,
    )


@router.get("", response_model=list[AssetOut])
async def list_assets(
    asset_class: str | None = Query(default=None, pattern="^(RENDA_FIXA|RENDA_VARIAVEL|FUNDOS|CRIPTO|OUTROS)$"),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    return [_asset_out(r) for r in await repo.list_assets(session, user.id, asset_class)]


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
async def create_asset(body: AssetIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    try:
        row = await repo.create_asset(
            session,
            user.id,
            body.ticker,
            body.name,
            body.asset_class,
            body.subtype,
            body.custodian,
            body.category_id,
            body.rate_type,
            body.rate,
            body.maturity_date,
        )
    except LookupError:
        raise not_found()
    except ValueError as e:
        raise unprocessable(str(e))
    return _asset_out(row)


@router.get("/{asset_id}", response_model=AssetOut)
async def get_asset(asset_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_asset(session, user.id, asset_id)
    if row is None:
        raise not_found()
    return _asset_out(row)


@router.patch("/{asset_id}", response_model=AssetOut)
async def patch_asset(
    asset_id: int, body: AssetPatch, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    from sqlalchemy import select

    from app.modules.finance.models import Category

    row = await repo.get_asset(session, user.id, asset_id)
    if row is None:
        raise not_found()
    data = body.model_dump(exclude_unset=True)
    if "category_id" in data and data["category_id"] is not None:
        res = await session.execute(
            select(Category).where(Category.id == data["category_id"], Category.user_id == user.id)
        )
        if res.scalar_one_or_none() is None:
            raise not_found()
    rate_type = data.get("rate_type", row.rate_type)
    rate = data.get("rate", row.rate)
    try:
        repo.validate_rate(row.asset_class, rate_type, rate)
    except ValueError as e:
        raise unprocessable(str(e))
    for k, v in data.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return _asset_out(row)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(asset_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    row = await repo.get_asset(session, user.id, asset_id)
    if row is None:
        raise not_found()
    ops = await repo.list_ops(session, user.id, asset_id)
    if ops:
        raise http_error(status.HTTP_409_CONFLICT, "Conflict", "Ativo possui operações; exclua-as antes")
    await repo.delete_asset(session, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{asset_id}/ops", response_model=list[OpOut])
async def list_ops(asset_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    try:
        rows = await repo.list_ops(session, user.id, asset_id)
    except LookupError:
        raise not_found()
    return [_op_out(r) for r in rows]


@router.post("/{asset_id}/ops", response_model=OpOut, status_code=status.HTTP_201_CREATED)
async def add_op(
    asset_id: int, body: OpIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    try:
        row = await repo.add_op(
            session,
            user.id,
            asset_id,
            body.kind,
            body.date,
            body.quantity,
            body.price,
            body.fees,
            body.amount,
            body.account_id,
            body.category_id,
        )
    except LookupError:
        raise not_found()
    except ValueError as e:
        raise unprocessable(str(e))
    return _op_out(row)


@router.delete("/{asset_id}/ops/{op_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_op(
    asset_id: int, op_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    if await repo.get_asset(session, user.id, asset_id) is None:
        raise not_found()
    if not await repo.delete_op(session, user.id, asset_id, op_id):
        raise not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{asset_id}/position", response_model=PositionOut)
async def get_position(asset_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    from datetime import date
    from decimal import Decimal

    from app.modules.market.prices import resolve_price

    row = await repo.get_asset(session, user.id, asset_id)
    if row is None:
        raise not_found()
    pos = await repo.get_position(session, user.id, asset_id)
    out = {
        "asset_id": asset_id,
        **{k: pos[k] for k in ("quantity", "average_price", "invested", "aportes", "resgates", "rendimentos")},
    }
    if pos["quantity"] > 0:
        q = await resolve_price(session, row, date.today())
        if q is not None:
            value = (q.price * pos["quantity"]).quantize(Decimal("0.01"))
            pnl = value + pos["resgates"] + pos["rendimentos"] - pos["aportes"]
            out |= {
                "current_price": q.price,
                "price_source": q.source,
                "price_as_of": q.as_of,
                "current_value": value,
                "pnl": pnl,
                "profitability": (pnl / pos["aportes"]).quantize(Decimal("0.0001")) if pos["aportes"] > 0 else None,
            }
    return PositionOut(**out)


@router.post("/{asset_id}/prices", response_model=PriceOut, status_code=status.HTTP_201_CREATED)
async def set_price(
    asset_id: int, body: PriceIn, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)
):
    try:
        out = await repo.set_manual_price(session, user.id, asset_id, body.date, body.price)
    except LookupError:
        raise not_found()
    return PriceOut(**out)


@router.get("/{asset_id}/prices", response_model=list[PriceOut])
async def price_history(asset_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    try:
        rows = await repo.price_history(session, user.id, asset_id)
    except LookupError:
        raise not_found()
    return [PriceOut(**r) for r in rows]


@router.get("/{asset_id}/returns", response_model=ReturnsOut)
async def get_returns(asset_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    from datetime import date

    try:
        out = await repo.get_returns(session, user.id, asset_id, date.today())
    except LookupError:
        raise not_found()
    return ReturnsOut(asset_id=asset_id, **out)
