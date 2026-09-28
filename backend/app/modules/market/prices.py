"""Orquestra preço atual: BRAPI (mercado) → ACCRUAL (RF contratada) → MANUAL.

Persiste snapshot diário em asset_prices (BRAPI/ACCRUAL) e usa Redis como
cache de 1h (fail-open). Preço staleness é sinalizado via `as_of`.
"""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.investments.models import Asset
from app.modules.market import accrual as acc_mod
from app.modules.market import bcb, brapi
from app.modules.market.models import AssetPrice


class Price(BaseModel):
    price: Decimal
    source: str  # BRAPI | ACCRUAL | MANUAL
    as_of: date


class PriceProvider(ABC):
    @abstractmethod
    async def quote(self, asset: Asset, ref: date, session: AsyncSession | None = None) -> Price | None: ...


class BrapiProvider(PriceProvider):
    async def quote(self, asset: Asset, ref: date, session: AsyncSession | None = None) -> Price | None:
        try:
            q = await brapi.get_quote(asset.ticker)
        except brapi.BrapiError:
            return None
        return Price(price=Decimal(str(q.price)), source="BRAPI", as_of=ref)


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
            .where(InvestmentOp.asset_id == asset.id, InvestmentOp.user_id == asset.user_id)
            .order_by(InvestmentOp.date, InvestmentOp.id)
        )
        lots: list[dict] = []
        for o in res.scalars().all():
            if o.kind == "APORTE":
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
    async def quote(self, asset: Asset, ref: date, session: AsyncSession | None = None) -> Price | None:
        assert session is not None, "ManualProvider.quote exige session"
        res = await session.execute(
            select(AssetPrice)
            .where(AssetPrice.asset_id == asset.id, AssetPrice.date <= ref)
            .order_by(AssetPrice.date.desc())
            .limit(1)
        )
        row = res.scalar_one_or_none()
        if row is None:
            return None
        return Price(price=row.price, source="MANUAL", as_of=row.date)


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
        await session.commit()


async def resolve_price(session: AsyncSession, asset: Asset, ref: date) -> Price | None:
    """BRAPI → ACCRUAL → MANUAL. Cache Redis 1h p/ BRAPI (fail-open)."""
    from app.core.redis_client import get_redis

    if asset.asset_class in ("RENDA_VARIAVEL", "FUNDOS", "CRIPTO") or (
        asset.asset_class == "RENDA_FIXA" and asset.subtype == "TESOURO"
    ):
        key = f"quote:{asset.ticker}:{ref.isoformat()}"
        try:
            redis = get_redis()
            cached = await redis.get(key)
            if cached:
                return Price(price=Decimal(cached), source="BRAPI", as_of=ref)
        except Exception:
            pass
        q = await BrapiProvider().quote(asset, ref)
        if q is not None:
            try:
                await get_redis().setex(key, 3600, str(q.price))
            except Exception:
                pass
            await _snapshot(session, asset, ref, q)
            return q
    if asset.asset_class == "RENDA_FIXA" and asset.rate_type in ("CDI_PCT", "PREFIXADO"):
        q = await AccrualProvider().quote(asset, ref, session)
        if q is not None:
            await _snapshot(session, asset, ref, q)
            return q
    return await ManualProvider().quote(asset, ref, session)
