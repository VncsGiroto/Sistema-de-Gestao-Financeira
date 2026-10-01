from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import conflict
from app.modules.finance.models import Category
from app.modules.investments.models import Asset, InvestmentOp
from app.modules.investments.position import position as calc_position
from app.modules.market.models import AssetPrice  # noqa: F401 — registra metadata p/ drop_all/create_all


async def _owned_category(session: AsyncSession, user_id: int, category_id: int | None):
    if category_id is None:
        return None
    res = await session.execute(select(Category).where(Category.id == category_id, Category.user_id == user_id))
    return res.scalar_one_or_none()


async def list_assets(session: AsyncSession, user_id: int, asset_class: str | None = None) -> list[Asset]:
    q = select(Asset).where(Asset.user_id == user_id)
    if asset_class:
        q = q.where(Asset.asset_class == asset_class)
    res = await session.execute(q.order_by(Asset.ticker))
    return list(res.scalars().all())


async def get_asset(session: AsyncSession, user_id: int, asset_id: int) -> Asset | None:
    res = await session.execute(select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id))
    return res.scalar_one_or_none()


async def create_asset(
    session: AsyncSession,
    user_id: int,
    ticker: str,
    name: str | None,
    asset_class: str,
    subtype: str,
    custodian: str | None,
    category_id: int | None,
    rate_type: str | None = None,
    rate=None,
    maturity_date=None,
) -> Asset:
    if category_id is not None and await _owned_category(session, user_id, category_id) is None:
        raise LookupError("category")
    validate_rate(asset_class, rate_type, rate)
    row = Asset(
        user_id=user_id,
        ticker=ticker.strip().upper(),
        name=name,
        asset_class=asset_class,
        subtype=subtype.strip().upper(),
        custodian=custodian,
        category_id=category_id,
        rate_type=rate_type,
        rate=rate,
        maturity_date=maturity_date,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise conflict("Ticker já cadastrado")
    await session.refresh(row)
    return row


async def delete_asset(session: AsyncSession, row: Asset) -> None:
    await session.delete(row)
    await session.commit()


async def list_ops(session: AsyncSession, user_id: int, asset_id: int) -> list[InvestmentOp]:
    asset = await get_asset(session, user_id, asset_id)
    if asset is None:
        raise LookupError("asset")
    res = await session.execute(
        select(InvestmentOp)
        .where(InvestmentOp.asset_id == asset_id, InvestmentOp.user_id == user_id)
        .order_by(InvestmentOp.date, InvestmentOp.id)
    )
    return list(res.scalars().all())


async def add_op(
    session: AsyncSession,
    user_id: int,
    asset_id: int,
    kind: str,
    on: date,
    quantity,
    price,
    fees: Decimal,
    amount,
    account_id: int | None = None,
    category_id: int | None = None,
) -> InvestmentOp:
    from app.modules.finance.models import Account, Transaction

    asset = await get_asset(session, user_id, asset_id)
    if asset is None:
        raise LookupError("asset")
    if kind in ("APORTE", "RESGATE"):
        if quantity is None or price is None:
            raise ValueError("APORTE/RESGATE exigem quantity e price")
        computed = (quantity * price + fees) if kind == "APORTE" else (quantity * price - fees)
        if computed <= 0:
            raise ValueError("Valor da operação deve ser positivo")
        if kind == "RESGATE":
            pos = await get_position(session, user_id, asset_id)
            if quantity > pos["quantity"]:
                raise ValueError("Quantidade maior que a posição")
        amount = computed
    else:  # RENDIMENTO
        if amount is None:
            raise ValueError("RENDIMENTO exige amount")
    row = InvestmentOp(
        user_id=user_id, asset_id=asset_id, kind=kind, date=on, quantity=quantity, price=price, fees=fees, amount=amount
    )
    session.add(row)
    await session.flush()
    if kind == "RENDIMENTO":
        # espelha no extrato como INCOME rastreável (simétrico ao pay de payables)
        if account_id is None:
            raise ValueError("RENDIMENTO exige account_id")
        res = await session.execute(select(Account).where(Account.id == account_id, Account.user_id == user_id))
        if res.scalar_one_or_none() is None:
            raise LookupError("account")
        cat = category_id if category_id is not None else asset.category_id
        if cat is not None:
            res = await session.execute(select(Category).where(Category.id == cat, Category.user_id == user_id))
            if res.scalar_one_or_none() is None:
                raise LookupError("category")
        tx = Transaction(
            user_id=user_id,
            account_id=account_id,
            category_id=cat,
            date=on,
            description=f"Rendimento {asset.ticker}",
            amount=amount,
            type="INCOME",
            source="MANUAL",
        )
        session.add(tx)
        await session.flush()
        row.transaction_id = tx.id
    await session.commit()
    await session.refresh(row)
    return row


async def delete_op(session: AsyncSession, user_id: int, asset_id: int, op_id: int) -> bool:
    from app.modules.finance.models import Transaction

    res = await session.execute(
        select(InvestmentOp).where(
            InvestmentOp.id == op_id, InvestmentOp.asset_id == asset_id, InvestmentOp.user_id == user_id
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        return False
    if row.transaction_id is not None:
        tx = await session.get(Transaction, row.transaction_id)
        if tx is not None and tx.user_id == user_id:
            await session.delete(tx)
    await session.delete(row)
    await session.commit()
    return True


async def get_position(session: AsyncSession, user_id: int, asset_id: int) -> dict:
    ops = await list_ops(session, user_id, asset_id)
    return calc_position(
        [{"kind": o.kind, "quantity": o.quantity, "price": o.price, "fees": o.fees, "amount": o.amount} for o in ops]
    )


def validate_rate(asset_class: str, rate_type: str | None, rate) -> None:
    if asset_class == "RENDA_FIXA" and rate_type is not None and rate is None:
        raise ValueError("rate_type exige rate")
    if rate_type is None and rate is not None:
        raise ValueError("rate exige rate_type")


async def set_manual_price(session: AsyncSession, user_id: int, asset_id: int, on, price) -> dict:
    asset = await get_asset(session, user_id, asset_id)
    if asset is None:
        raise LookupError("asset")
    res = await session.execute(
        select(AssetPrice).where(AssetPrice.asset_id == asset_id, AssetPrice.date == on, AssetPrice.source == "MANUAL")
    )
    row = res.scalar_one_or_none()
    if row is None:
        row = AssetPrice(user_id=user_id, asset_id=asset_id, date=on, price=price, source="MANUAL")
        session.add(row)
    else:
        row.price = price
    await session.commit()
    await session.refresh(row)
    return {"id": row.id, "date": row.date, "price": row.price, "source": row.source}


async def price_history(session: AsyncSession, user_id: int, asset_id: int) -> list[dict]:
    asset = await get_asset(session, user_id, asset_id)
    if asset is None:
        raise LookupError("asset")
    res = await session.execute(select(AssetPrice).where(AssetPrice.asset_id == asset_id).order_by(AssetPrice.date))
    return [{"id": r.id, "date": r.date, "price": r.price, "source": r.source} for r in res.scalars().all()]


async def get_returns(session: AsyncSession, user_id: int, asset_id: int, end) -> dict:
    """Simples + XIRR + TWR + benchmarks. Sem preço => métricas temporais None."""
    from app.modules.investments import returns as ret
    from app.modules.market import benchmarks as bench
    from app.modules.market.prices import resolve_price

    asset = await get_asset(session, user_id, asset_id)
    if asset is None:
        raise LookupError("asset")
    ops = await list_ops(session, user_id, asset_id)
    if not ops:
        return {
            "start": None,
            "end": end,
            "simple": None,
            "xirr": None,
            "twr": None,
            "twr_annualized": None,
            "benchmarks": {},
        }
    start = ops[0].date

    prices = await price_history(session, user_id, asset_id)
    hist = sorted(((p["date"], Decimal(p["price"])) for p in prices), key=lambda x: x[0])

    def price_at(d):
        cands = [pr for dt, pr in hist if dt <= d]
        if cands:
            return cands[-1]
        for o in ops:
            if o.date <= d and o.price:
                return Decimal(o.price)
        return None

    pos = await get_position(session, user_id, asset_id)
    cur = await resolve_price(session, asset, end)
    cur_value = (cur.price * pos["quantity"]).quantize(Decimal("0.01")) if cur and pos["quantity"] > 0 else None

    # XIRR: aportes −, resgates/rendimentos +, valor atual como fluxo final
    flows = []
    for o in ops:
        amt = Decimal(o.amount)
        flows.append((o.date, -amt if o.kind == "APORTE" else amt))
    if cur_value is not None and cur_value > 0:
        flows.append((end, cur_value))
    xirr = ret.xirr(flows)

    # TWR por cotas: value antes de cada fluxo + valor final
    events, qty, twr_ok = [], Decimal("0"), True
    for o in ops:
        p = price_at(o.date)
        if p is None:
            twr_ok = False
            break
        value_before = qty * p
        amt = Decimal(o.amount)
        flow = -amt if o.kind in ("RESGATE", "RENDIMENTO") else amt
        events.append({"date": o.date, "flow": flow, "value": value_before})
        qty += (
            Decimal(o.quantity or 0)
            if o.kind == "APORTE"
            else (-Decimal(o.quantity or 0) if o.kind == "RESGATE" else Decimal("0"))
        )
    twr = twr_ann = None
    if twr_ok and cur_value is not None:
        events.append({"date": end, "flow": Decimal("0"), "value": cur_value})
        twr = ret.unitize(events)
        if twr is not None:
            twr_ann = ret.annualize(twr, (end - start).days)

    simple = None
    if pos["aportes"] > 0 and cur_value is not None:
        simple = (cur_value + pos["resgates"] + pos["rendimentos"] - pos["aportes"]) / pos["aportes"]

    benchmarks = {
        "cdi": await bench.cdi_return(start, end),
        "ipca": await bench.ipca_return(start, end),
    }
    return {
        "start": start,
        "end": end,
        "simple": simple,
        "xirr": xirr,
        "twr": twr,
        "twr_annualized": twr_ann,
        "benchmarks": benchmarks,
    }
