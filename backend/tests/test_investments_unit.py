"""7.1 unit: posição derivada do ledger (puro, sem DB)."""

from decimal import Decimal

from app.modules.investments.position import position


def test_aporte_unico():
    p = position([{"kind": "APORTE", "quantity": Decimal("10"), "price": Decimal("40"),
                   "fees": Decimal("5"), "amount": Decimal("405")}])
    assert p["quantity"] == Decimal("10")
    assert p["average_price"] == Decimal("40.5")
    assert p["invested"] == Decimal("405")
    assert p["aportes"] == Decimal("405") and p["resgates"] == 0 and p["rendimentos"] == 0


def test_preco_medio_ponderado():
    p = position([
        {"kind": "APORTE", "quantity": Decimal("10"), "price": Decimal("40"), "fees": Decimal("0"), "amount": Decimal("400")},
        {"kind": "APORTE", "quantity": Decimal("10"), "price": Decimal("60"), "fees": Decimal("0"), "amount": Decimal("600")},
    ])
    assert p["average_price"] == Decimal("50")
    assert p["invested"] == Decimal("1000")


def test_resgate_reduz_qtd_mantem_medio():
    p = position([
        {"kind": "APORTE", "quantity": Decimal("10"), "price": Decimal("40"), "fees": Decimal("0"), "amount": Decimal("400")},
        {"kind": "RESGATE", "quantity": Decimal("4"), "price": Decimal("50"), "fees": Decimal("0"), "amount": Decimal("200")},
    ])
    assert p["quantity"] == Decimal("6")
    assert p["average_price"] == Decimal("40")
    assert p["invested"] == Decimal("240")
    assert p["resgates"] == Decimal("200")


def test_rendimento_nao_mexe_posicao():
    p = position([
        {"kind": "APORTE", "quantity": Decimal("10"), "price": Decimal("40"), "fees": Decimal("0"), "amount": Decimal("400")},
        {"kind": "RENDIMENTO", "quantity": None, "price": None, "fees": Decimal("0"), "amount": Decimal("25")},
    ])
    assert p["quantity"] == Decimal("10") and p["rendimentos"] == Decimal("25")


def test_vazio():
    p = position([])
    assert p["quantity"] == 0 and p["average_price"] == 0 and p["invested"] == 0
