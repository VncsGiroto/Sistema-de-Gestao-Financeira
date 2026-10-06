"""Visão unificada de eventos patrimoniais (leitura; não duplica registros).

Uma linha por evento: Transaction (receita/despesa, incl. rendimento espelhado),
LedgerMovement (transferência, aporte, resgate) e InvestmentOp de REINVESTIMENTO
(sem efeito no caixa). Rendimento aparece uma única vez, pela transação vinculada
enriquecida com a operação. Filtros e contagens por fonte no banco; merge em
memória com ordem total fixa (data desc, fonte, id desc).
"""

from datetime import date as date_t
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance.models import Account, Transaction
from app.modules.investments.models import Asset, InvestmentOp
from app.modules.ledger.models import LedgerMovement
from app.modules.movements.schemas import MovementItem

KINDS = ("INCOME", "EXPENSE", "TRANSFER", "APORTE", "RESGATE", "RENDIMENTO", "REINVESTIMENTO")
_TX_KINDS = ("INCOME", "EXPENSE", "RENDIMENTO")
_LEDGER_KINDS = ("TRANSFER", "APORTE", "RESGATE")
_SOURCE_RANK = {"ledger": 0, "tx": 1, "op": 2}


def validate_kinds(kinds: list[str] | None) -> set[str]:
    wanted = set(KINDS if not kinds else kinds)
    unknown = wanted - set(KINDS)
    if unknown:
        raise ValueError(f"kind inválido: {sorted(unknown)}")
    return wanted


async def _linked_tx_ids(session: AsyncSession, user_id: int) -> set[int]:
    res = await session.execute(
        select(InvestmentOp.transaction_id).where(
            InvestmentOp.user_id == user_id, InvestmentOp.transaction_id.is_not(None)
        )
    )
    return {tx_id for (tx_id,) in res.all()}


def _direction(kind: str, account_id: int | None, from_id: int | None, to_id: int | None, tx_type: str = "") -> str:
    """Sem conta: efeito absoluto (transferência é neutra no consolidado)."""
    if kind == "REINVESTIMENTO":
        return "neutral"
    if account_id is None:
        if kind == "TRANSFER":
            return "neutral"
        if kind in ("APORTE", "EXPENSE"):
            return "out"
        return "in"
    if kind == "TRANSFER":
        return "in" if to_id == account_id else "out"
    if kind == "APORTE":
        return "out"
    if kind == "RESGATE":
        return "in"
    return "in" if tx_type == "INCOME" else "out"


def _impact(direction: str, amount: Decimal) -> Decimal:
    if direction == "in":
        return Decimal(amount).quantize(Decimal("0.01"))
    if direction == "out":
        return (-Decimal(amount)).quantize(Decimal("0.01"))
    return Decimal("0.00")


async def query_movements(
    session: AsyncSession,
    user_id: int,
    from_: date_t | None = None,
    to: date_t | None = None,
    account_id: int | None = None,
    kinds: list[str] | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[MovementItem], int]:
    wanted = validate_kinds(kinds)
    if account_id is not None:
        acc = (
            await session.execute(select(Account.id).where(Account.id == account_id, Account.user_id == user_id))
        ).scalar_one_or_none()
        if acc is None:
            raise LookupError("account")

    items: list[MovementItem] = []
    total = 0

    # --- Transactions (receita/despesa; rendimento = vinculada, uma única linha) ---
    if wanted & set(_TX_KINDS):
        want_inc, want_exp, want_rend = "INCOME" in wanted, "EXPENSE" in wanted, "RENDIMENTO" in wanted
        if not kinds:
            want_inc = want_exp = want_rend = True
        tx_q = select(Transaction).where(Transaction.user_id == user_id)
        if from_ is not None:
            tx_q = tx_q.where(Transaction.date >= from_)
        if to is not None:
            tx_q = tx_q.where(Transaction.date <= to)
        if account_id is not None:
            tx_q = tx_q.where(Transaction.account_id == account_id)
        count_q = select(func.count()).select_from(tx_q.subquery())
        total += (await session.execute(count_q)).scalar() or 0
        linked = await _linked_tx_ids(session, user_id)
        rows = (await session.execute(tx_q.order_by(Transaction.date.desc(), Transaction.id.desc()))).scalars().all()
        for t in rows:
            is_linked = t.id in linked
            if is_linked:
                if not want_rend:
                    continue
                kind = "RENDIMENTO"
            elif t.type == "INCOME":
                if not want_inc:
                    continue
                kind = "INCOME"
            else:
                if not want_exp:
                    continue
                kind = "EXPENSE"
            direction = _direction(kind, account_id, None, None, t.type)
            items.append(
                MovementItem(
                    id=f"tx:{t.id}",
                    kind=kind,
                    date=t.date,
                    description=t.description,
                    amount=t.amount,
                    direction=direction,
                    cash_impact=_impact(direction, Decimal(t.amount)),
                    account_id=t.account_id,
                    transaction_id=t.id,
                    category_id=t.category_id,
                    editable=not is_linked,
                    origin="operation" if is_linked else "transaction",
                    origin_hint=(
                        "Gerada por rendimento; edite ou exclua pela operação de investimento"
                        if is_linked
                        else "Lançamento manual"
                    ),
                )
            )

    # --- Ledger (transferência, aporte, resgate) ---
    if wanted & set(_LEDGER_KINDS):
        led_kinds = [k for k in _LEDGER_KINDS if k in wanted] if kinds else list(_LEDGER_KINDS)
        led_q = select(LedgerMovement).where(LedgerMovement.user_id == user_id, LedgerMovement.kind.in_(led_kinds))
        if from_ is not None:
            led_q = led_q.where(LedgerMovement.date >= from_)
        if to is not None:
            led_q = led_q.where(LedgerMovement.date <= to)
        if account_id is not None:
            led_q = led_q.where(
                (LedgerMovement.from_account_id == account_id) | (LedgerMovement.to_account_id == account_id)
            )
        total += (await session.execute(select(func.count()).select_from(led_q.subquery()))).scalar() or 0
        moves = (
            (await session.execute(led_q.order_by(LedgerMovement.date.desc(), LedgerMovement.id.desc())))
            .scalars()
            .all()
        )
        op_ids = [m.op_id for m in moves if m.op_id is not None]
        ops_by_id = {}
        if op_ids:
            op_rows = (await session.execute(select(InvestmentOp).where(InvestmentOp.id.in_(op_ids)))).scalars().all()
            ops_by_id = {o.id: o for o in op_rows}
        asset_ids = {o.asset_id for o in ops_by_id.values()}
        tickers = {}
        if asset_ids:
            for a in (await session.execute(select(Asset).where(Asset.id.in_(asset_ids)))).scalars().all():
                tickers[a.id] = a.ticker
        for m in moves:
            op = ops_by_id.get(m.op_id) if m.op_id is not None else None
            ticker = tickers.get(op.asset_id) if op is not None else None
            direction = _direction(m.kind, account_id, m.from_account_id, m.to_account_id)
            transfer = m.kind == "TRANSFER"
            items.append(
                MovementItem(
                    id=f"ledger:{m.id}",
                    kind=m.kind,
                    date=m.date,
                    description=m.description,
                    amount=m.amount,
                    direction=direction,
                    cash_impact=_impact(direction, Decimal(m.amount)),
                    account_id=account_id,
                    from_account_id=m.from_account_id,
                    to_account_id=m.to_account_id,
                    asset_id=op.asset_id if op is not None else m.asset_id,
                    ticker=ticker,
                    op_id=m.op_id,
                    movement_id=m.id,
                    editable=transfer,
                    origin="transfer" if transfer else "operation",
                    origin_hint=(
                        "Transferência avulsa; excluir reverte os dois lados"
                        if transfer
                        else "Gerado por operação de investimento; altere pela operação"
                    ),
                )
            )

    # --- Reinvestimento (op sem caixa; visível na conta do ativo) ---
    if "REINVESTIMENTO" in wanted:
        op_q = (
            select(InvestmentOp, Asset.ticker, Asset.account_id)
            .join(Asset, Asset.id == InvestmentOp.asset_id)
            .where(
                InvestmentOp.user_id == user_id,
                InvestmentOp.kind == "REINVESTIMENTO",
                Asset.user_id == user_id,
            )
        )
        if from_ is not None:
            op_q = op_q.where(InvestmentOp.date >= from_)
        if to is not None:
            op_q = op_q.where(InvestmentOp.date <= to)
        if account_id is not None:
            op_q = op_q.where(Asset.account_id == account_id)
        total += (await session.execute(select(func.count()).select_from(op_q.subquery()))).scalar() or 0
        for o, ticker, asset_account in (
            await session.execute(op_q.order_by(InvestmentOp.date.desc(), InvestmentOp.id.desc()))
        ).all():
            items.append(
                MovementItem(
                    id=f"op:{o.id}",
                    kind="REINVESTIMENTO",
                    date=o.date,
                    description=f"Reinvestimento {ticker}",
                    amount=o.amount,
                    direction="neutral",
                    cash_impact=_impact("neutral", Decimal(o.amount)),
                    account_id=asset_account if account_id is not None else None,
                    asset_id=o.asset_id,
                    ticker=ticker,
                    op_id=o.id,
                    editable=False,
                    origin="operation",
                    origin_hint="Evento de posição, sem efeito no caixa; altere pela operação",
                )
            )

    items.sort(key=lambda i: (-i.date.toordinal(), _SOURCE_RANK[i.id.split(":")[0]], -int(i.id.split(":")[1])))
    start = (page - 1) * per_page
    return items[start : start + per_page], total
