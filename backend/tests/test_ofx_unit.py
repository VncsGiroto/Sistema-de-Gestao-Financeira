"""3.1 unit: parse + normalização puros (sem DB)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.imports.normalizer import OfxImporter, clean_description, normalize
from app.modules.imports.ofx_parser import OfxParseError, normalize_headers, parse_ofx

FIX = Path(__file__).parent / "fixtures"
importer = OfxImporter()


def test_parse_minimo():
    raws = parse_ofx((FIX / "minimo.ofx").read_bytes())
    assert len(raws) == 3
    assert raws[0].fitid == "20260910001"
    assert raws[0].date == date(2026, 9, 10)
    assert raws[0].amount == Decimal("-250.50")


def test_normalize_campos():
    raws = parse_ofx((FIX / "minimo.ofx").read_bytes())
    n = normalize(raws[0], account_id=7)
    assert n is not None
    assert n.external_id == "20260910001"
    assert n.account_id == 7 and n.source == "OFX"
    assert n.type == "EXPENSE" and n.amount == Decimal("-250.50")
    assert n.description == "SUPERMERCADO XYZ COMPRA CARTAO FINAL 1234"

    inc = normalize(raws[1], account_id=7)
    assert inc is not None and inc.type == "INCOME"


def test_linha_zerada_invalida():
    raws = parse_ofx((FIX / "minimo.ofx").read_bytes())
    assert normalize(raws[2], account_id=7) is None


def test_arquivo_invalido_erro_legivel():
    with pytest.raises(OfxParseError):
        parse_ofx((FIX / "invalido.ofx").read_bytes())
    with pytest.raises(OfxParseError):
        parse_ofx(b"   ")


def test_external_id_estavel_sem_fitid():
    from app.modules.imports.ofx_parser import RawTx

    r = RawTx(fitid=None, date=date(2026, 9, 1), amount=Decimal("-10"), memo="X", name="Y", trntype="DEBIT")
    a = normalize(r, account_id=1)
    b = normalize(r, account_id=1)
    assert a is not None and b is not None and a.external_id == b.external_id


def test_clean_description():
    assert clean_description("Café João's *1234!") == "CAFE JOAO S 1234"


def test_c6_headers_exoticos():
    """Regressão: C6 emite `ENCODING: UTF - 8` (com espaços) que quebrava o ofxparse."""
    raw = (FIX / "c6.ofx").read_bytes()
    norm = normalize_headers(raw)
    assert b"ENCODING:UTF-8" in norm
    raws = parse_ofx(raw)
    assert len(raws) == 4
    assert raws[0].fitid == "TESTC6FIT0001"
    assert raws[0].date == date(2026, 7, 15)
    assert raws[0].amount == Decimal("1075.68")
    # sem MEMO: name vazio, normaliza para SEM DESCRICAO mas não é INVALID
    n = normalize(raws[2], account_id=3)
    assert n is not None and n.external_id == "TESTC6FIT0003"
