"""0018b unit: ganho acumulado por ponto (puro, sem DB)."""

from datetime import date
from decimal import Decimal

from app.modules.investments.portfolio import cumulative_gains


def test_primeiro_ponto_zera():
    out = cumulative_gains([(date(2026, 1, 10), Decimal("1000.00"))], [])
    assert out == {date(2026, 1, 10): Decimal("0.00")}


def test_rendimento_conta_aporte_nao():
    out = cumulative_gains(
        [(date(2026, 1, 10), Decimal("1000.00")), (date(2026, 2, 1), Decimal("1100.00"))],
        [],
    )
    assert out[date(2026, 2, 1)] == Decimal("100.00")


def test_aporte_posterior_abate_resgate_soma():
    out = cumulative_gains(
        [
            (date(2026, 1, 10), Decimal("1000.00")),
            (date(2026, 2, 1), Decimal("1700.00")),  # +600 aportados, +100 rendidos
            (date(2026, 3, 1), Decimal("600.00")),  # resgatou 1100, restou 600
        ],
        [(date(2026, 1, 20), Decimal("600.00")), (date(2026, 2, 15), Decimal("-1100.00"))],
    )
    assert out[date(2026, 2, 1)] == Decimal("100.00")
    assert out[date(2026, 3, 1)] == Decimal("100.00")


def test_vazio():
    assert cumulative_gains([], [(date(2026, 1, 1), Decimal("10.00"))]) == {}
