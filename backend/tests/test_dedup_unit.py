"""3.2 unit: similaridade, normalização e regra fuzzy (sem DB)."""

from datetime import date
from decimal import Decimal

from app.modules.imports.duplicate_detector import (
    Candidate,
    is_fuzzy,
    norm_description,
    similarity,
)


def test_norm_remove_ruido():
    assert norm_description("Ifood *1234 LTDA!") == "IFOOD"
    assert norm_description("  Café   S.A.  ") == "CAFE"


def test_similarity_identicas():
    assert similarity("IFOOD JANTAR", "IFOOD JANTAR") == 1.0


def test_similarity_diferentes():
    assert similarity("NETFLIX", "SPOTIFY") < 0.70


def test_similarity_ordem_trocada():
    assert similarity("SALARIO EMPRESA ABC", "EMPRESA ABC SALARIO") >= 0.70


def _cand(**kw):
    base = {
        "id": 1,
        "account_id": 5,
        "date": date(2026, 9, 10),
        "description": "IFOOD JANTAR",
        "amount": Decimal("45.90"),
    }
    base.update(kw)
    return Candidate(**base)


def test_fuzzy_match():
    ok, score = is_fuzzy(5, date(2026, 9, 11), "IFOOD JANTAR", Decimal("45.90"), _cand())
    assert ok and score == 1.0


def test_fuzzy_fora_da_janela():
    ok, _ = is_fuzzy(5, date(2026, 9, 13), "IFOOD JANTAR", Decimal("45.90"), _cand(), window_days=2)
    assert not ok
    ok, _ = is_fuzzy(5, date(2026, 9, 13), "IFOOD JANTAR", Decimal("45.90"), _cand(), window_days=3)
    assert ok


def test_fuzzy_outra_conta_ou_valor():
    ok, _ = is_fuzzy(6, date(2026, 9, 10), "IFOOD JANTAR", Decimal("45.90"), _cand())
    assert not ok
    ok, _ = is_fuzzy(5, date(2026, 9, 10), "IFOOD JANTAR", Decimal("45.91"), _cand())
    assert not ok


def test_fuzzy_descricao_diferente():
    ok, _ = is_fuzzy(5, date(2026, 9, 10), "NETFLIX", Decimal("45.90"), _cand())
    assert not ok
