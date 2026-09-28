"""Posição derivada do ledger. Puro e unit testável (opera sobre dicts)."""

from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


def _money(d) -> Decimal:
    """Quantiza valores monetários para 2 casas (BRL)."""
    return Decimal(d).quantize(_CENT, rounding=ROUND_HALF_UP)


def _qty(d) -> Decimal:
    """Normaliza quantidade removendo zeros à direita (16.00000000 → 16)."""
    d = Decimal(d)
    if d == 0:
        return Decimal("0")
    return d.normalize()


def position(ops: list[dict]) -> dict:
    """ops: [{kind, quantity?, price?, fees, amount}]. Retorna posição consolidada."""
    qty = Decimal("0")
    cost_qty = Decimal("0")  # qty comprada acumulada (p/ preço médio)
    cost_total = Decimal("0")  # custo total dos aportes (qty*price + fees)
    aportes = Decimal("0")
    resgates = Decimal("0")
    rendimentos = Decimal("0")
    for o in ops:
        q = Decimal(o.get("quantity") or 0)
        amt = Decimal(o["amount"])
        if o["kind"] == "APORTE":
            qty += q
            cost_qty += q
            cost_total += amt
            aportes += amt
        elif o["kind"] == "RESGATE":
            qty -= q
            resgates += amt
        elif o["kind"] == "RENDIMENTO":
            rendimentos += amt
    avg = (cost_total / cost_qty) if cost_qty > 0 else Decimal("0")
    avg = _money(avg)
    qty = _qty(qty)
    return {
        "quantity": qty,
        "average_price": avg,
        "invested": _money(avg * qty),  # custo da posição atual pelo preço médio
        "aportes": _money(aportes),
        "resgates": _money(resgates),
        "rendimentos": _money(rendimentos),
    }
