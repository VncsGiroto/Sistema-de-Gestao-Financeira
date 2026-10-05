"""Orquestra preço atual: ACCRUAL (RF contratada) → MANUAL_OVERRIDE explícito → MANUAL.

Sem commit interno: `_snapshot` só dá flush; o commit é do chamador (limite do repositório).
Sem fallback silencioso: RF com contrato nunca usa MANUAL comum.
"""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.investments.models import Asset
from app.modules.market import accrual as acc_mod
from app.modules.market import bcb
from app.modules.market.models import AssetPrice


class Price(BaseModel):
    price: Decimal
    source: str  # ACCRUAL | MANUAL | MANUAL_OVERRIDE
    as_of: date


class PriceProvider(ABC):
    @abstractmethod
    async def quote(self, asset: Asset, ref: date, session: AsyncSession | None = None) -> Price | None: ...


class AccrualProvider(PriceProvider):
    async def quote(self, asset: Asset, ref: date, session: AsyncSession | None = None) -> Price | None:
        if asset.asset_class != "RENDA_FIXA" or asset.rate_type not in ("CDI_PCT", "PREFIXADO"):
            return None
        rate_type = asset.rate_type
        rate = asset.rate
        if rate is None:
            return None
        assert session is not None, "AccrualProvider.quote exige session"
        from app.modules.investments.models import InvestmentOp

        res = await session.execute(
            select(InvestmentOp)
            .where(InvestmentOp.asset_id == asset.id, InvestmentOp.user_id == asset.user_id, InvestmentOp.date <= ref)
            .order_by(InvestmentOp.date, InvestmentOp.id)
        )
        lots: list[dict] = []
        for o in res.scalars().all():
            if o.kind in ("APORTE", "REINVESTIMENTO"):
                if o.quantity is None or o.price is None:
                    return None
                lots.append({"qty": o.quantity, "price": o.price, "date": o.date})
            elif o.kind == "RESGATE":
                if o.quantity is None:
                    return None
                try:
                    lots = acc_mod.consume_fifo(lots, o.quantity)
                except ValueError:
                    return None
        if not lots:
            return None
        start = min(lot["date"] for lot in lots)
        cdi = {}
        if rate_type == "CDI_PCT":
            try:
                cdi = await bcb.cdi_range(start, ref)
            except bcb.BcbError:
                return None
        try:
            value = acc_mod.accrue_lots(lots, rate_type, rate, ref, cdi)
        except ValueError:
            return None
        qty = sum((lot["qty"] for lot in lots), Decimal("0"))
        if qty <= 0:
            return None
        return Price(price=value / qty, source="ACCRUAL", as_of=ref)


class ManualProvider(PriceProvider):
    def __init__(self, sources: tuple[str, ...] = ("MANUAL",)) -> None:
        self.sources = sources

    async def quote(self, asset: Asset, ref: date, session: AsyncSession | None = None) -> Price | None:
        assert session is not None, "ManualProvider.quote exige session"
        res = await session.execute(
            select(AssetPrice)
            .where(AssetPrice.asset_id == asset.id, AssetPrice.date <= ref, AssetPrice.source.in_(self.sources))
            .order_by(AssetPrice.date.desc())
            .limit(1)
        )
        row = res.scalar_one_or_none()
        if row is None:
            return None
        return Price(price=row.price, source=row.source, as_of=row.date)


async def _snapshot(session: AsyncSession, asset: Asset, ref: date, price: Price) -> None:
    res = await session.execute(
        select(AssetPrice).where(
            AssetPrice.asset_id == asset.id, AssetPrice.date == ref, AssetPrice.source == price.source
        )
    )
    if res.scalar_one_or_none() is None:
        session.add(
            AssetPrice(user_id=asset.user_id, asset_id=asset.id, date=ref, price=price.price, source=price.source)
        )
        await session.flush()


async def resolve_price(session: AsyncSession, asset: Asset, ref: date) -> Price | None:
    """RF com contrato: só ACCRUAL ou override explícito. Demais: MANUAL. Sem fallback silencioso."""
    contracted = asset.asset_class == "RENDA_FIXA" and asset.rate_type in ("CDI_PCT", "PREFIXADO")
    if contracted:
        q = await AccrualProvider().quote(asset, ref, session)
        if q is not None:
            await _snapshot(session, asset, ref, q)
            return q
        return await ManualProvider(("MANUAL_OVERRIDE",)).quote(asset, ref, session)
    return await ManualProvider().quote(asset, ref, session)


async def contract_quote(session: AsyncSession, asset: Asset, ref: date) -> Decimal | None:
    """Cotação unitária do contrato na data, para converter valor (R$) em quantidade.

    Sem posição anterior (primeiro aporte ou pós-resgate total): 1,00000000.
    None quando o accrual não consegue precificar (ex.: BCB fora).
    """
    from app.modules.investments.models import InvestmentOp
    from app.modules.investments.position import position as calc_position

    res = await session.execute(
        select(InvestmentOp).where(
            InvestmentOp.asset_id == asset.id, InvestmentOp.user_id == asset.user_id, InvestmentOp.date <= ref
        )
    )
    ops = [
        {"kind": o.kind, "quantity": o.quantity, "price": o.price, "fees": o.fees, "amount": o.amount}
        for o in res.scalars().all()
    ]
    pos = calc_position(ops)
    if pos["quantity"] <= 0:
        return Decimal("1")
    q = await AccrualProvider().quote(asset, ref, session)
    return q.price if q is not None else None
