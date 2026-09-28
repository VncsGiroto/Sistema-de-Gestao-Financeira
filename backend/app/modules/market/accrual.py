"""Accrual de renda fixa por lotes FIFO. Puro e unit testável.

Suporta CDI_PCT e PREFIXADO (a.a., 252 du). IPCA_MAIS: preço manual.
Dias úteis = seg–sex (sem feriados) — aproximação documentada.
"""

from datetime import date, timedelta
from decimal import Decimal


def is_business_day(d: date) -> bool:
    return d.weekday() < 5


def business_days(start: date, end: date) -> list[date]:
    """Dias úteis em [start, end)."""
    out, d = [], start
    while d < end:
        if is_business_day(d):
            out.append(d)
        d += timedelta(days=1)
    return out


def cdi_factor(pct: Decimal, days: list[date], cdi: dict) -> Decimal:
    """Fator Π(1+cdi/100)^(pct/100) nos dias úteis (cdi ausente = 0)."""
    f = Decimal("1")
    for d in days:
        c = cdi.get(d, Decimal("0"))
        f *= (Decimal("1") + c / Decimal("100")) ** (pct / Decimal("100"))
    return f


def prefixado_factor(annual: Decimal, du: int) -> Decimal:
    return (Decimal("1") + annual / Decimal("100")) ** (Decimal(du) / Decimal("252"))


def accrue_lots(lots: list[dict], rate_type: str, rate: Decimal, ref: date, cdi: dict) -> Decimal:
    """lots: [{qty, price, date}]. Retorna valor atual total na data ref."""
    total = Decimal("0")
    for lot in lots:
        days = business_days(lot["date"], ref)
        if rate_type == "CDI_PCT":
            f = cdi_factor(rate, days, cdi)
        elif rate_type == "PREFIXADO":
            f = prefixado_factor(rate, len(days))
        else:
            raise ValueError(f"Accrual não suportado para {rate_type} (use preço manual)")
        total += Decimal(lot["qty"]) * Decimal(lot["price"]) * f
    return total


def consume_fifo(lots: list[dict], qty: Decimal) -> list[dict]:
    """Baixa qty dos lotes (FIFO). Retorna os lotes restantes."""
    rest, left = [], qty
    for lot in lots:
        if left <= 0:
            rest.append(lot)
            continue
        take = min(Decimal(lot["qty"]), left)
        left -= take
        if Decimal(lot["qty"]) - take > 0:
            rest.append({**lot, "qty": Decimal(lot["qty"]) - take})
    if left > 0:
        raise ValueError("Quantidade maior que os lotes")
    return rest
