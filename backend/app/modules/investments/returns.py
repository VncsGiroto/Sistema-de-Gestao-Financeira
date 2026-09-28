"""XIRR (money-weighted) e TWR (time-weighted, por cotas). Puros, sem I/O.

Convenção de sinais: aporte = negativo (sai do bolso), resgate/rendimento/valor
final = positivo. Retornos anualizados em base 365.25.
"""

from datetime import date
from decimal import Decimal


def annualize(r: Decimal, days: int) -> Decimal | None:
    if days <= 0:
        return None
    return (Decimal("1") + r) ** (Decimal("365.25") / Decimal(days)) - Decimal("1")


def _npv(rate: float, flows: list[tuple[date, float]]) -> float:
    d0 = flows[0][0]
    return sum(a / ((1 + rate) ** ((d - d0).days / 365.25)) for d, a in flows)


def xirr(flows: list[tuple[date, Decimal]], guess: float = 0.1) -> Decimal | None:
    """TIR anualizada dos fluxos datados. None se insolúvel (sem troca de sinal)."""
    if len(flows) < 2:
        return None
    fs = sorted(flows)
    amts = [float(a) for _, a in fs]
    if not (any(a < 0 for a in amts) and any(a > 0 for a in amts)):
        return None
    if len({d for d, _ in fs}) == 1:
        return None
    f = [(d, float(a)) for d, a in fs]
    # Newton-Raphson com derivada numérica
    r = guess
    for _ in range(100):
        v = _npv(r, f)
        if abs(v) < 1e-9:
            return Decimal(str(r))
        h = 1e-6 * (1 + abs(r))
        d = (_npv(r + h, f) - v) / h
        if d == 0:
            break
        r -= v / d
        if r <= -1:
            r = -0.9999
    else:
        return Decimal(str(r))
    # fallback: bissecção em [-0.9999, 10]
    lo, hi = -0.9999, 10.0
    vlo, vhi = _npv(lo, f), _npv(hi, f)
    if vlo * vhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if _npv(lo, f) * _npv(mid, f) <= 0:
            hi = mid
        else:
            lo = mid
    return Decimal(str((lo + hi) / 2))


def unitize(events: list[dict]) -> Decimal | None:
    """TWR do período via cotas.

    events: [{date, flow, value}] onde value = valor da carteira ANTES do flow
    (flow>0 = aporte; flow<0 = retirada/distribuição). Último evento deve ter
    flow=0 e value = valor final. Cota inicial = 1.
    """
    if len(events) < 2:
        return None
    evs = sorted(events, key=lambda e: e["date"])
    units = Decimal("0")
    price = Decimal("1")
    for e in evs:
        v, f = Decimal(e["value"]), Decimal(e["flow"])
        if units == 0:
            if v + f <= 0:
                return None
            units = (v + f) / price
        else:
            price = v / units
            if price <= 0:
                return None
            units += f / price
    if units <= 0:
        return None
    return price - Decimal("1")
