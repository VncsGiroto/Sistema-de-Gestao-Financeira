"""Estimativa gerencial do valor líquido de um resgate total (IR estimado). Puro e unit testável.

NÃO constitui apuração fiscal: considera só IR sobre o ganho (atual − investido),
ignora IOF, day-trade, isenção de R$ 20k/mês em ações e come-cotas. Serve somente
para exibição ("est."); nunca altera ledger, posição, caixa ou rentabilidade.
"""

from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")

# Regressiva de RF por dias desde o primeiro aporte: (dias_limite, alíquota %).
RF_BRACKETS: tuple[tuple[int, Decimal], ...] = (
    (180, Decimal("22.5")),
    (360, Decimal("20")),
    (720, Decimal("17.5")),
)
RF_LONG = Decimal("15")
OTHER_AUTO = Decimal("15")  # ação/fundos/cripto/outros: 15% sobre o lucro
RF_UNKNOWN_TERM = Decimal("22.5")  # prazo desconhecido: alíquota mais conservadora


def auto_rate(asset_class: str, days_held: int | None) -> Decimal:
    """Alíquota automática (%) pela classe; RF usa a regressiva pelo prazo."""
    if asset_class == "RENDA_FIXA":
        if days_held is None:
            return RF_UNKNOWN_TERM
        for limit, rate in RF_BRACKETS:
            if days_held <= limit:
                return rate
        return RF_LONG
    return OTHER_AUTO


def estimate_net(
    *,
    current_value: Decimal | None,
    invested: Decimal,
    days_held: int | None,
    asset_class: str,
    tax_rate: Decimal | None,
) -> dict:
    """Retorna {gross, gain, rate, rate_source, tax, net}; Nones sem preço atual."""
    rate = Decimal(tax_rate) if tax_rate is not None else auto_rate(asset_class, days_held)
    source = "manual" if tax_rate is not None else "auto"
    if current_value is None:
        return {"gross": None, "gain": None, "rate": rate, "rate_source": source, "tax": None, "net": None}
    gain = (Decimal(current_value) - Decimal(invested)).quantize(_CENT, rounding=ROUND_HALF_UP)
    if gain <= 0:
        return {
            "gross": Decimal(current_value),
            "gain": gain,
            "rate": rate,
            "rate_source": source,
            "tax": Decimal("0.00"),
            "net": Decimal(current_value),
        }
    tax = (gain * rate / Decimal("100")).quantize(_CENT, rounding=ROUND_HALF_UP)
    return {
        "gross": Decimal(current_value),
        "gain": gain,
        "rate": rate,
        "rate_source": source,
        "tax": tax,
        "net": (Decimal(current_value) - tax).quantize(_CENT, rounding=ROUND_HALF_UP),
    }
