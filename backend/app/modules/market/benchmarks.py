"""Benchmarks no período: CDI (BCB), Ibovespa (brapi), IPCA (BCB)."""

from datetime import date
from decimal import Decimal

from app.modules.market import bcb
from app.modules.market import history as hist_mod


async def cdi_return(start: date, end: date) -> Decimal | None:
    try:
        series = await bcb.cdi_range(start, end)
    except bcb.BcbError:
        return None
    f = Decimal("1")
    for d, c in series.items():
        if start <= d <= end:
            f *= Decimal("1") + c / Decimal("100")
    return (f - Decimal("1")) if series else None


async def ibov_return(start: date, end: date) -> Decimal | None:
    try:
        pts = await hist_mod.history("^BVSP", start, end)
    except Exception:
        return None
    if len(pts) < 2 or pts[0]["close"] == 0:
        return None
    return Decimal(str(pts[-1]["close"] / pts[0]["close"] - 1))


async def ipca_return(start: date, end: date) -> Decimal | None:
    """Encadeia as variações mensais cheias contidas no período."""
    try:
        series = await bcb.series("433", start.replace(day=1), end)
    except bcb.BcbError:
        return None
    f = Decimal("1")
    used = False
    for d, v in sorted(series.items()):
        # competência do mês d integralmente dentro de [start, end]
        first = d.replace(day=1)
        import calendar as _cal

        last = first.replace(day=_cal.monthrange(first.year, first.month)[1])
        if first >= start.replace(day=1) and last <= end:
            f *= Decimal("1") + v / Decimal("100")
            used = True
    return (f - Decimal("1")) if used else None
