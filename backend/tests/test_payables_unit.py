"""Payables unit: rateio de desconto + vencimentos + schedule (puros, sem DB)."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.payables.due_dates import next_due_date
from app.modules.payables.schedule import apportion, schedule


def test_sem_desconto_identidade():
    amounts = [Decimal("333.33"), Decimal("333.33"), Decimal("333.34")]
    assert apportion(amounts, Decimal("0")) == amounts


def test_rateio_proporcional_soma():
    amounts = [Decimal("333.33"), Decimal("333.33"), Decimal("333.34")]
    out = apportion(amounts, Decimal("150"))
    assert sum(out) == Decimal("850.00")
    assert all(v > 0 for v in out)
    # proporcional: quotas ~iguais (parcelas iguais)
    assert max(out) - min(out) <= Decimal("0.02")


def test_rateio_desproporcional():
    out = apportion([Decimal("900"), Decimal("100")], Decimal("100"))
    assert sum(out) == Decimal("900.00")
    assert out[0] == Decimal("810.00") and out[1] == Decimal("90.00")


def test_desconto_invalido():
    with pytest.raises(ValueError):
        apportion([Decimal("100")], Decimal("-1"))
    with pytest.raises(ValueError):
        apportion([Decimal("100")], Decimal("100"))
    with pytest.raises(ValueError):
        apportion([Decimal("100")], Decimal("150"))


def test_desconto_nao_zera_parcela():
    with pytest.raises(ValueError):
        apportion([Decimal("990"), Decimal("10")], Decimal("999.99"))


def test_next_due_monthly():
    assert next_due_date("FIXED", "MONTHLY", 10, date(2026, 9, 5)) == date(2026, 9, 10)
    assert next_due_date("FIXED", "MONTHLY", 10, date(2026, 9, 15)) == date(2026, 10, 10)


def test_schedule_soma():
    out = schedule(Decimal("1000"), 3, date(2026, 9, 10))
    assert [s["amount"] for s in out] == [Decimal("333.33"), Decimal("333.33"), Decimal("333.34")]
    assert sum(s["amount"] for s in out) == Decimal("1000")
