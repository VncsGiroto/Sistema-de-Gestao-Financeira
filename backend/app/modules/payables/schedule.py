"""Cronograma de parcelas. Puro e unit testável.

Regra de arredondamento: cada parcela é o total dividido, truncado no centavo;
a ÚLTIMA absorve a diferença, garantindo soma == total.
Vencimentos mensais a partir de first_due_date (com clamp p/ meses curtos).
"""

import calendar
from datetime import date
from decimal import ROUND_DOWN, Decimal


def _add_months(ref: date, months: int) -> date:
    m = ref.month - 1 + months
    year, month = ref.year + m // 12, m % 12 + 1
    return date(year, month, min(ref.day, calendar.monthrange(year, month)[1]))


def schedule(total: Decimal, n: int, first_due: date) -> list[dict]:
    if n < 2:
        raise ValueError("Mínimo de 2 parcelas")
    if total <= 0:
        raise ValueError("Total deve ser positivo")
    base = (total / n).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    out = []
    acc = Decimal("0")
    for i in range(1, n + 1):
        amount = total - acc if i == n else base
        acc += amount
        out.append({"n": i, "due_date": _add_months(first_due, i - 1), "amount": amount})
    return out


def apportion(amounts: list[Decimal], discount: Decimal) -> list[Decimal]:
    """Rateia `discount` proporcionalmente aos valores (trunca no centavo,
    resto na última). Soma do retorno == soma(amounts) - discount."""
    total = sum(amounts, Decimal("0"))
    if discount < 0 or discount >= total:
        raise ValueError("Desconto deve estar entre 0 (inclusive) e o total (exclusive)")
    if discount == 0:
        return list(amounts)
    out, acc, target = [], Decimal("0"), total - discount
    for i, a in enumerate(amounts):
        share = target - acc if i == len(amounts) - 1 else (a * target / total).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        if share <= 0:
            raise ValueError("Desconto zera uma parcela")
        acc += share
        out.append(share)
    return out
