"""Consolidação da carteira: caixa + posições, fluxos e snapshots (épico investimentos↔contas)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance import repository as finance_repo
from app.modules.investments import repository as inv_repo
from app.modules.investments import returns as ret
from app.modules.investments.models import PortfolioSnapshot
from app.modules.market.prices import resolve_price


async def compute_portfolio(session: AsyncSession, user_id: int, ref: date | None = None) -> dict:
    """Agrega caixa das contas INVESTMENT + posições avaliadas. Sem média de rentabilidades."""
    ref = ref or date.today()
    accounts = await finance_repo.list_accounts(session, user_id)
    sums = await finance_repo.account_summaries(session, user_id)
    cash = Decimal("0")
    patrimonio_cash = Decimal("0")
    by_account: dict[int, dict] = {}
    for a in accounts:
        s = sums.get(a.id, {})
        cur = a.initial_balance + s.get("income", Decimal("0")) - s.get("expense", Decimal("0"))
        cur += s.get("ledger_in", Decimal("0")) - s.get("ledger_out", Decimal("0"))
        patrimonio_cash += cur
        if a.account_type != "INVESTMENT":
            continue
        cash += cur
        by_account[a.id] = {"name": a.name, "cash": cur}

    assets = await inv_repo.list_assets(session, user_id)
    positions: list = []
    by_class: dict[str, Decimal] = {}
    aportes = reinvest = resgates = rendimentos = Decimal("0")
    flows: list[tuple[date, Decimal]] = []
    unpriced: list[str] = []
    for asset in assets:
        pos = await inv_repo.get_position(session, user_id, asset.id)
        aportes += pos["aportes"]
        reinvest += pos["reinvestimentos"]
        resgates += pos["resgates"]
        rendimentos += pos["rendimentos"]
        ops = await inv_repo.list_ops(session, user_id, asset.id)
        for o in ops:
            if o.kind == "REINVESTIMENTO":
                continue
            amt = Decimal(o.amount)
            flows.append((o.date, -amt if o.kind == "APORTE" else amt))
        cur = await resolve_price(session, asset, ref)
        value = (cur.price * pos["quantity"]).quantize(Decimal("0.01")) if cur and pos["quantity"] > 0 else None
        if value is None:
            if pos["quantity"] > 0:
                unpriced.append(asset.ticker)
        else:
            by_class[asset.asset_class] = by_class.get(asset.asset_class, Decimal("0")) + value
            if asset.account_id is not None and asset.account_id in by_account:
                by_account[asset.account_id]["value"] = by_account[asset.account_id].get("value", Decimal("0")) + value
        positions.append(
            {
                "asset_id": asset.id,
                "ticker": asset.ticker,
                "asset_class": asset.asset_class,
                "account_id": asset.account_id,
                "quantity": pos["quantity"],
                "average_price": pos["average_price"],
                "invested": pos["invested"],
                "current_price": cur.price if cur else None,
                "price_source": cur.source if cur else None,
                "value": value,
            }
        )
    positions_value = sum((p["value"] for p in positions if p["value"] is not None), Decimal("0"))
    total = cash + positions_value
    patrimonio = patrimonio_cash + positions_value
    net_invested = aportes + reinvest - resgates
    resultado = total - net_invested
    if positions_value > 0:
        flows.append((ref, positions_value))
    xirr = ret.xirr(flows)

    snaps = await session.execute(
        select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user_id).order_by(PortfolioSnapshot.date)
    )
    snapshots = [
        {"date": s.date, "cash": s.cash, "positions_value": s.positions_value, "total": s.total}
        for s in snaps.scalars().all()
    ]
    return {
        "cash": cash,
        "positions_value": positions_value,
        "total": total,
        "patrimonio": patrimonio,
        "aportes": aportes,
        "reinvestimentos": reinvest,
        "resgates": resgates,
        "rendimentos": rendimentos,
        "net_invested": net_invested,
        "resultado": resultado,
        "xirr": xirr,
        "positions": positions,
        "unpriced": unpriced,
        "by_class": [{"name": k, "total": v} for k, v in sorted(by_class.items())],
        "by_account": [
            {"account_id": aid, "name": v["name"], "cash": v["cash"], "value": v.get("value", Decimal("0"))}
            for aid, v in sorted(by_account.items())
        ],
        "snapshots": snapshots,
        "history_since": snapshots[0]["date"] if snapshots else None,
    }


async def record_snapshot(session: AsyncSession, user_id: int, on: date | None = None) -> None:
    """Upsert do snapshot do dia (último estado vence). Chamado sob evento."""
    on = on or date.today()
    data = await compute_portfolio(session, user_id, on)
    res = await session.execute(
        select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user_id, PortfolioSnapshot.date == on)
    )
    row = res.scalar_one_or_none()
    if row is None:
        row = PortfolioSnapshot(user_id=user_id, date=on, cash=0, positions_value=0, total=0)
        session.add(row)
    row.cash = data["cash"]
    row.positions_value = data["positions_value"]
    row.total = data["total"]
    await session.commit()
