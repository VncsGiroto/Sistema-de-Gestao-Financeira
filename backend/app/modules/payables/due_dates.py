"""Regras de vencimento de contas a pagar. Puro e unit testável."""

import calendar
from datetime import date, timedelta


def next_due_date(kind: str, periodicity: str | None, due_day: int | None, ref: date) -> date:
    """Calcula o próximo vencimento a partir da data de referência.

    ONE_TIME não é calculado aqui: o cliente informa `next_due` (data cheia).
    """
    if kind == "ONE_TIME":
        raise ValueError("ONE_TIME usa next_due informado pelo cliente")
    if periodicity == "WEEKLY":
        if due_day is None or not 1 <= due_day <= 7:
            raise ValueError("WEEKLY exige due_day entre 1 (seg) e 7 (dom)")
        # due_day = dia da semana ISO (1=segunda ... 7=domingo)
        delta = (due_day - ref.isoweekday()) % 7
        return ref + timedelta(days=delta)
    if periodicity in ("MONTHLY", "YEARLY"):
        if due_day is None or not 1 <= due_day <= 31:
            raise ValueError("MONTHLY/YEARLY exige due_day entre 1 e 31")
        if periodicity == "MONTHLY":
            cand = _clamp(ref.year, ref.month, due_day)
            if cand < ref:
                cand = _clamp(*_next_month(ref.year, ref.month), due_day)
            return cand
        cand = _clamp(ref.year, ref.month, due_day)
        if cand < ref:
            cand = _clamp(ref.year + 1, ref.month, due_day)
        return cand
    raise ValueError("kind/periodicity inválidos")


def _clamp(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)
