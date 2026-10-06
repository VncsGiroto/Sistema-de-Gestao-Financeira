"""Consolidação da carteira: caixa + posições, fluxos e snapshots (épico investimentos↔contas)."""

from datetime import date
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance import repository as finance_repo
from app.modules.finance.models import Transaction
from app.modules.investments import repository as inv_repo
from app.modules.investments import returns as ret
from app.modules.investments.models import InvestmentOp, PortfolioSnapshot
from app.modules.ledger.models import LedgerMovement
from app.modules.market import bcb
from app.modules.market.prices import resolve_price


async def compute_portfolio(
    session: AsyncSession, user_id: int, ref: date | None = None, persist_prices: bool = False
) -> dict:
    """Agrega caixa das contas INVESTMENT + posições avaliadas. Sem média de rentabilidades.

    Tudo é calculado "na data de referência": operações, transações, ledger,
    snapshots e preços com data posterior a `ref` são ignorados. `persist_prices`
    grava snapshots do accrual (só em operações com commit; GETs usam False).
    """
    ref = ref or date.today()
    accounts = await finance_repo.list_accounts(session, user_id)
    sums = await finance_repo.account_summaries(session, user_id, ref)
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
    unpriced: list[str] = []
    for asset in assets:
        pos = await inv_repo.get_position(session, user_id, asset.id, ref)
        aportes += pos["aportes"]
        reinvest += pos["reinvestimentos"]
        resgates += pos["resgates"]
        rendimentos += pos["rendimentos"]
        try:
            cur = await resolve_price(session, asset, ref, persist_prices)
        except (bcb.BcbError, httpx.HTTPError):
            cur = None  # fail-open só p/ falha do provedor; erro de banco/programação propaga
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

    # Fluxos externos à boundary INVESTMENT (+entra, −sai): transferências que cruzam a
    # boundary e INCOME/EXPENSE direto em conta INVESTMENT. Operações internas (aporte da
    # corretora p/ o ativo etc.) não aparecem aqui.
    inv_ids = {a.id for a in accounts if a.account_type == "INVESTMENT"}
    ext: list[tuple[date, Decimal]] = []
    if inv_ids:
        led = await session.execute(
            select(LedgerMovement).where(
                LedgerMovement.user_id == user_id,
                LedgerMovement.kind == "TRANSFER",
                LedgerMovement.date <= ref,
            )
        )
        for m in led.scalars().all():
            if m.to_account_id in inv_ids and m.from_account_id not in inv_ids:
                ext.append((m.date, Decimal(m.amount)))
            elif m.from_account_id in inv_ids and m.to_account_id not in inv_ids:
                ext.append((m.date, -Decimal(m.amount)))
        # Receitas espelhadas por RENDIMENTO são retorno interno, não aporte externo.
        linked = await session.execute(
            select(InvestmentOp.transaction_id).where(
                InvestmentOp.user_id == user_id,
                InvestmentOp.transaction_id.is_not(None),
                InvestmentOp.date <= ref,
            )
        )
        linked_ids = {tx_id for (tx_id,) in linked.all()}
        txs = await session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.account_id.in_(inv_ids),
                Transaction.date <= ref,
            )
        )
        for t in txs.scalars().all():
            if t.id in linked_ids:
                continue
            ext.append((t.date, Decimal(t.amount) if t.type == "INCOME" else -Decimal(t.amount)))
    ext_in = sum((a for _, a in ext if a > 0), Decimal("0"))
    ext_out = -sum((a for _, a in ext if a < 0), Decimal("0"))
    net_invested = ext_in - ext_out
    resultado = total + ext_out - ext_in

    xirr_flows = [(d, -a) for d, a in ext]
    if total > 0:
        xirr_flows.append((ref, total))
    xirr = ret.xirr(xirr_flows)

    # TWR da carteira: unitiza a série de snapshots com fluxos alocados no primeiro
    # snapshot na data ou após cada fluxo (aproximação documentada e esparsa).
    snaps = await session.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == user_id, PortfolioSnapshot.date <= ref)
        .order_by(PortfolioSnapshot.date)
    )
    snap_rows = list(snaps.scalars().all())
    twr = None
    if len(snap_rows) >= 2:
        events = [{"date": snap_rows[0].date, "flow": Decimal("0"), "value": Decimal(snap_rows[0].total)}]
        for prev, snap in zip(snap_rows, snap_rows[1:]):
            flow = sum((a for d, a in ext if prev.date < d <= snap.date), Decimal("0"))
            events.append({"date": snap.date, "flow": flow, "value": Decimal(snap.total) - flow})
        twr = ret.unitize(events)
    snapshots = [
        {"date": s.date, "cash": s.cash, "positions_value": s.positions_value, "total": s.total} for s in snap_rows
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
        "twr": twr,
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


async def upsert_snapshot(session: AsyncSession, user_id: int, on: date | None = None) -> None:
    """Upsert do snapshot do dia com flush (sem commit: mesma transação do chamador)."""
    on = on or date.today()
    data = await compute_portfolio(session, user_id, on, persist_prices=True)
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
    await session.flush()


async def record_snapshot(session: AsyncSession, user_id: int, on: date | None = None) -> None:
    """Upsert do snapshot do dia (último estado vence). Chamado sob evento."""
    await upsert_snapshot(session, user_id, on)
    await session.commit()
