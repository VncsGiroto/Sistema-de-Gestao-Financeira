from datetime import date as date_t
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance.models import Account
from app.modules.ledger.models import LedgerMovement


class LedgerError(ValueError):
    pass


async def _owned_account(session: AsyncSession, user_id: int, account_id: int) -> Account | None:
    res = await session.execute(select(Account).where(Account.id == account_id, Account.user_id == user_id))
    return res.scalar_one_or_none()


async def create_transfer(
    session: AsyncSession,
    user_id: int,
    from_account_id: int,
    to_account_id: int,
    amount: Decimal,
    on: date_t,
    description: str | None,
) -> LedgerMovement:
    if from_account_id == to_account_id:
        raise LedgerError("Origem e destino devem ser contas diferentes")
    if await _owned_account(session, user_id, from_account_id) is None:
        raise LookupError("from_account")
    if await _owned_account(session, user_id, to_account_id) is None:
        raise LookupError("to_account")
    row = LedgerMovement(
        user_id=user_id,
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        kind="TRANSFER",
        amount=amount,
        date=on,
        description=(description or "Transferência").strip(),
    )
    session.add(row)
    await session.flush()
    # O caixa da corretora mudou: reconstrói a série desde a data do evento (para frente).
    from app.modules.investments import portfolio as pf

    await pf.rebuild_snapshots(session, user_id, since=on)
    await session.commit()
    await session.refresh(row)
    return row


async def list_movements(session: AsyncSession, user_id: int, account_id: int | None = None) -> list[LedgerMovement]:
    q = select(LedgerMovement).where(LedgerMovement.user_id == user_id)
    if account_id is not None:
        q = q.where((LedgerMovement.from_account_id == account_id) | (LedgerMovement.to_account_id == account_id))
    res = await session.execute(q.order_by(LedgerMovement.date.desc(), LedgerMovement.id.desc()))
    return list(res.scalars().all())


async def get_movement(session: AsyncSession, user_id: int, movement_id: int) -> LedgerMovement | None:
    res = await session.execute(
        select(LedgerMovement).where(LedgerMovement.id == movement_id, LedgerMovement.user_id == user_id)
    )
    return res.scalar_one_or_none()


async def delete_movement(session: AsyncSession, row: LedgerMovement) -> None:
    if row.kind != "TRANSFER":
        raise LedgerError("Movimento ligado a operação só pode ser revertido pela operação")
    on = row.date
    user_id = row.user_id
    await session.delete(row)
    await session.flush()
    from app.modules.investments import portfolio as pf

    await pf.rebuild_snapshots(session, user_id, since=on)
    await session.commit()


async def account_ledger_sums(session: AsyncSession, user_id: int, end: date_t | None = None) -> dict[int, dict]:
    """{account_id: {ledger_in, ledger_out}} em 2 GROUP BYs. `end` = corte as-of."""
    out: dict[int, dict] = {}
    ins_q = select(LedgerMovement.to_account_id, func.sum(LedgerMovement.amount)).where(
        LedgerMovement.user_id == user_id, LedgerMovement.to_account_id.is_not(None)
    )
    outs_q = select(LedgerMovement.from_account_id, func.sum(LedgerMovement.amount)).where(
        LedgerMovement.user_id == user_id, LedgerMovement.from_account_id.is_not(None)
    )
    if end is not None:
        ins_q = ins_q.where(LedgerMovement.date <= end)
        outs_q = outs_q.where(LedgerMovement.date <= end)
    if end is not None:
        ins_q = ins_q.where(LedgerMovement.date <= end)
        outs_q = outs_q.where(LedgerMovement.date <= end)
    ins = await session.execute(ins_q.group_by(LedgerMovement.to_account_id))
    for account_id, total in ins.all():
        out.setdefault(account_id, {"in": Decimal("0"), "out": Decimal("0")})["in"] = total or Decimal("0")
    outs = await session.execute(outs_q.group_by(LedgerMovement.from_account_id))
    for account_id, total in outs.all():
        out.setdefault(account_id, {"in": Decimal("0"), "out": Decimal("0")})["out"] = total or Decimal("0")
    return out
