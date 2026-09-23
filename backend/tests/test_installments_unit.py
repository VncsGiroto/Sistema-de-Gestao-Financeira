"""4.2 unit: cronograma e arredondamento (puro, sem DB)."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.installments.schedule import schedule


def test_divisao_exata():
    out = schedule(Decimal("6000"), 12, date(2026, 9, 10))
    assert len(out) == 12
    assert all(s["amount"] == Decimal("500.00") for s in out)
    assert sum(s["amount"] for s in out) == Decimal("6000")
    assert out[0]["due_date"] == date(2026, 9, 10)
    assert out[11]["due_date"] == date(2027, 8, 10)


def test_resto_na_ultima():
    out = schedule(Decimal("1000"), 3, date(2026, 9, 10))
    assert [s["amount"] for s in out] == [Decimal("333.33"), Decimal("333.33"), Decimal("333.34")]
    assert sum(s["amount"] for s in out) == Decimal("1000")


def test_clamp_mes_curto():
    out = schedule(Decimal("200"), 2, date(2026, 1, 31))
    assert out[1]["due_date"] == date(2026, 2, 28)


def test_virada_ano():
    out = schedule(Decimal("200"), 3, date(2026, 11, 15))
    assert [s["due_date"].month for s in out] == [11, 12, 1]


def test_validacoes():
    with pytest.raises(ValueError):
        schedule(Decimal("100"), 1, date(2026, 9, 10))
    with pytest.raises(ValueError):
        schedule(Decimal("0"), 2, date(2026, 9, 10))
    with pytest.raises(ValueError):
        schedule(Decimal("-5"), 2, date(2026, 9, 10))
