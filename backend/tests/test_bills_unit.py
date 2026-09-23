"""4.1 unit: cálculo de next_due (puro, sem DB)."""

from datetime import date

import pytest

from app.modules.bills.due_dates import next_due_date


def test_monthly_mesmo_mes():
    assert next_due_date("RECURRING", "MONTHLY", 10, date(2026, 9, 5)) == date(2026, 9, 10)


def test_monthly_proximo_mes():
    assert next_due_date("FIXED", "MONTHLY", 10, date(2026, 9, 15)) == date(2026, 10, 10)


def test_monthly_ano_novo():
    assert next_due_date("FIXED", "MONTHLY", 5, date(2026, 12, 20)) == date(2027, 1, 5)


def test_monthly_clamp_fevereiro():
    assert next_due_date("FIXED", "MONTHLY", 31, date(2026, 2, 1)) == date(2026, 2, 28)


def test_weekly():
    # 2026-09-22 é terça; próxima sexta (5) = 25
    assert next_due_date("RECURRING", "WEEKLY", 5, date(2026, 9, 22)) == date(2026, 9, 25)
    # mesmo dia = hoje
    assert next_due_date("RECURRING", "WEEKLY", 2, date(2026, 9, 22)) == date(2026, 9, 22)


def test_weekly_invalido():
    with pytest.raises(ValueError):
        next_due_date("RECURRING", "WEEKLY", 31, date(2026, 9, 22))


def test_yearly():
    assert next_due_date("FIXED", "YEARLY", 10, date(2026, 9, 5)) == date(2026, 9, 10)
    assert next_due_date("FIXED", "YEARLY", 10, date(2026, 9, 15)) == date(2027, 9, 10)


def test_one_time_nao_calculado():
    with pytest.raises(ValueError):
        next_due_date("ONE_TIME", None, None, date(2026, 9, 22))
