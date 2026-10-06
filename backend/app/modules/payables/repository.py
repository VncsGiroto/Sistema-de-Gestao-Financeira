from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.audit_models import AuditLog
from app.modules.finance.models import Account, Category, Transaction
from app.modules.payables.due_dates import next_due_date
from app.modules.payables.models import Payable
from app.modules.payables.schedule import apportion, schedule


class PayableError(ValueError):
    pass


def _validate_shape(
    kind: str, amount, periodicity, due_day, next_due, total_amount, num_installments, first_due_date
) -> None:
    if kind in ("FIXED", "RECURRING"):
        if amount is None or periodicity is None or due_day is None:
            raise PayableError("FIXED/RECURRING exigem amount, periodicity e due_day")
        if periodicity == "WEEKLY" and not 1 <= due_day <= 7:
            raise PayableError("WEEKLY exige due_day entre 1 e 7")
        if next_due is not None:
            raise PayableError("next_due de recorrente é calculado pelo servidor")
        if any(v is not None for v in (total_amount, num_installments, first_due_date)):
            raise PayableError("Recorrente não usa campos de parcela")
    elif kind == "INSTALLMENT":
        if total_amount is None or num_installments is None or first_due_date is None:
            raise PayableError("INSTALLMENT exige total_amount, num_installments e first_due_date")
        if any(v is not None for v in (amount, periodicity, due_day, next_due)):
            raise PayableError("INSTALLMENT não usa amount/periodicity/due_day/next_due")
    elif kind == "ONE_TIME":
        if amount is None or next_due is None:
            raise PayableError("ONE_TIME exige amount e next_due")
        if any(v is not None for v in (periodicity, due_day, total_amount, num_installments, first_due_date)):
            raise PayableError("ONE_TIME não usa campos de recorrência/parcela")
    else:
        raise PayableError("kind inválido")


async def _owned(session: AsyncSession, model, user_id: int, row_id: int | None):
    if row_id is None:
        return None
    res = await session.execute(select(model).where(model.id == row_id, model.user_id == user_id))
    return res.scalar_one_or_none()


async def list_all(session: AsyncSession, user_id: int, kind: str | None = None) -> list[Payable]:
    q = select(Payable).where(Payable.user_id == user_id)
    if kind:
        q = q.where(Payable.kind == kind)
    res = await session.execute(q.order_by(Payable.id))
    return list(res.scalars().all())


async def upcoming(session: AsyncSession, user_id: int, days: int, ref: date) -> list[Payable]:
    rows = await list_all(session, user_id)
    out = [r for r in rows if _ref_due(r, ref) is not None and _ref_due(r, ref) <= ref + timedelta(days=days)]
    out.sort(key=lambda r: (_ref_due(r, ref), r.description))
    return out


def _ref_due(row: Payable, ref: date):
    """Próximo vencimento de referência: next_due, ou 1ª parcela não-paga."""
    if row.kind == "INSTALLMENT":
        for s in build_schedule(row):
            if s["n"] not in (row.paid_ns or []):
                return s["due_date"]
        return None
    return row.next_due


async def get_one(session: AsyncSession, user_id: int, payable_id: int) -> Payable | None:
    res = await session.execute(select(Payable).where(Payable.id == payable_id, Payable.user_id == user_id))
    return res.scalar_one_or_none()


async def create(
    session: AsyncSession,
    user_id: int,
    description: str,
    kind: str,
    amount,
    periodicity,
    due_day,
    next_due,
    total_amount,
    num_installments,
    first_due_date,
    account_id: int | None,
    category_id: int | None,
    ref: date,
) -> Payable | None:
    """Retorna None se account/category não pertencerem ao usuário."""
    _validate_shape(kind, amount, periodicity, due_day, next_due, total_amount, num_installments, first_due_date)
    if await _owned(session, Account, user_id, account_id) is None and account_id is not None:
        return None
    if await _owned(session, Category, user_id, category_id) is None and category_id is not None:
        return None
    resolved_next = None
    inst_amount = None
    if kind in ("FIXED", "RECURRING"):
        try:
            resolved_next = next_due_date(kind, periodicity, due_day, ref)
        except ValueError as e:
            raise PayableError(str(e))
    elif kind == "ONE_TIME":
        resolved_next = next_due  # informado pelo cliente; sem ele a conta nunca aparece na agenda
    elif kind == "INSTALLMENT":
        try:
            schedule(total_amount, num_installments, first_due_date)
        except ValueError as e:
            raise PayableError(str(e))
        # referência exibida: parcela truncada; valores exatos via schedule
        from decimal import ROUND_DOWN

        inst_amount = (total_amount / num_installments).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    row = Payable(
        user_id=user_id,
        description=description.strip(),
        kind=kind,
        amount=amount,
        periodicity=periodicity,
        due_day=due_day,
        next_due=resolved_next,
        total_amount=total_amount,
        num_installments=num_installments,
        installment_amount=inst_amount,
        first_due_date=first_due_date,
        paid_ns=[],
        account_id=account_id,
        category_id=category_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def delete(session: AsyncSession, row: Payable) -> None:
    from app.modules.finance.models import Transaction

    linked = await session.execute(
        select(func.count()).select_from(Transaction).where(Transaction.payable_id == row.id)
    )
    if (linked.scalar() or 0) > 0:
        raise PayableError("Conta possui lançamentos gerados; exclua-os no extrato antes de excluir a conta")
    await session.delete(row)
    await session.commit()


def build_schedule(row: Payable) -> list[dict]:
    if row.kind != "INSTALLMENT":
        raise PayableError("Schedule só existe para INSTALLMENT")
    if row.total_amount is None or row.num_installments is None or row.first_due_date is None:
        raise PayableError("INSTALLMENT exige total_amount, num_installments e first_due_date")
    paid = set(row.paid_ns or [])
    return [{**s, "paid": s["n"] in paid} for s in schedule(row.total_amount, row.num_installments, row.first_due_date)]


async def pay(
    session: AsyncSession,
    user_id: int,
    row: Payable,
    account_id: int,
    amount,
    paid_on: date,
    category_id: int | None,
    ns: list[int] | None,
    discount,
) -> list[Transaction]:
    """Baixa a conta gerando transação(ões) source=PAYABLE. Retorna as txs criadas."""
    # Lock pessimista na linha: duas baixas concorrentes precisam se serializar
    # antes das verificações de estado (pago/não-pago, parcelas). populate_existing
    # garante atributos frescos: o objeto pode já estar no identity map da sessão
    # (carregado pelo router antes de chamar pay).
    locked = (
        await session.execute(
            select(Payable)
            .where(Payable.id == row.id, Payable.user_id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if locked is None:
        raise LookupError("payable")
    row = locked
    account = await _owned(session, Account, user_id, account_id)
    if account is None:
        raise LookupError("account")
    cat = category_id if category_id is not None else row.category_id
    if cat is not None:
        owned = await _owned(session, Category, user_id, cat)
        if owned is None:
            raise LookupError("category")
        if owned.type != "EXPENSE":
            raise PayableError("Categoria incompatível: a baixa gera uma despesa")
    discount = discount or Decimal("0")
    txs: list[Transaction] = []

    if row.kind == "ONE_TIME":
        if row.paid_at is not None:
            raise PayableError("Conta única já paga")
        if ns is not None:
            raise PayableError("ONE_TIME não usa ns")
        value = amount or row.amount
        txs.append(_tx(user_id, account_id, cat, paid_on, f"{row.description}", value, row.id))
        row.paid_at = datetime.now(UTC)
    elif row.kind in ("FIXED", "RECURRING"):
        if ns is not None:
            raise PayableError("Recorrente não usa ns")
        value = amount or row.amount
        if row.kind == "FIXED" and value != row.amount:
            raise PayableError("FIXED tem valor fixo; use o amount cadastrado")
        txs.append(_tx(user_id, account_id, cat, paid_on, f"{row.description}", value, row.id))
        if row.kind == "RECURRING" and amount is not None and amount != row.amount:
            row.amount = amount  # estimativa atualizada pelo valor pago
        try:
            base = paid_on + timedelta(days=1)
            if row.next_due is not None:
                after_current = row.next_due + timedelta(days=1)
                if after_current > base:
                    base = after_current
            row.next_due = next_due_date(row.kind, row.periodicity, row.due_day, base)
        except ValueError as e:
            raise PayableError(str(e))
    elif row.kind == "INSTALLMENT":
        if amount is not None:
            raise PayableError("INSTALLMENT usa valores do schedule; informe ns + discount")
        sched = build_schedule(row)
        unpaid = [s for s in sched if not s["paid"]]
        targets = [s for s in sched if s["n"] in (ns or [])] if ns else unpaid[:1]
        if not targets:
            raise PayableError("Nenhuma parcela a pagar (informe ns ou quite o restante)")
        if any(s["paid"] for s in targets):
            raise PayableError("Uma das parcelas já foi paga")
        gross = [s["amount"] for s in targets]
        try:
            nets = apportion(gross, discount)
        except ValueError as e:
            raise PayableError(str(e))
        for s, net in zip(targets, nets):
            txs.append(
                _tx(
                    user_id,
                    account_id,
                    cat,
                    paid_on,
                    f"{row.description} ({s['n']}/{row.num_installments})",
                    net,
                    row.id,
                )
            )
        row.paid_ns = sorted(set(row.paid_ns or []) | {s["n"] for s in targets})
    else:
        raise PayableError("kind inválido")

    for t in txs:
        session.add(t)
    await session.flush()
    session.add(
        AuditLog(
            user_id=user_id,
            action="payable.pay",
            entity="payables",
            entity_id=row.id,
            meta={"tx_ids": [t.id for t in txs], "discount": str(discount), "ns": ns or [], "kind": row.kind},
            created_at=datetime.now(UTC),
        )
    )
    await session.commit()
    for t in txs:
        await session.refresh(t)
    await session.refresh(row)
    return txs


def _tx(
    user_id: int,
    account_id: int,
    category_id: int | None,
    on: date,
    description: str,
    amount: Decimal | None,
    payable_id: int,
) -> Transaction:
    if amount is None or amount <= 0:
        raise PayableError("Valor da baixa deve ser positivo")
    return Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        date=on,
        description=description[:500],
        amount=amount,
        type="EXPENSE",
        source="PAYABLE",
        payable_id=payable_id,
    )
