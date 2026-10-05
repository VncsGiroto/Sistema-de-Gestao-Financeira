"""7.1 unit: posição derivada do ledger (puro, sem DB)."""

from decimal import Decimal

from app.modules.investments.position import position


def test_aporte_unico():
    p = position(
        [
            {
                "kind": "APORTE",
                "quantity": Decimal("10"),
                "price": Decimal("40"),
                "fees": Decimal("5"),
                "amount": Decimal("405"),
            }
        ]
    )
    assert p["quantity"] == Decimal("10")
    assert p["average_price"] == Decimal("40.5")
    assert p["invested"] == Decimal("405")
    assert p["aportes"] == Decimal("405") and p["resgates"] == 0 and p["rendimentos"] == 0


def test_preco_medio_ponderado():
    p = position(
        [
            {
                "kind": "APORTE",
                "quantity": Decimal("10"),
                "price": Decimal("40"),
                "fees": Decimal("0"),
                "amount": Decimal("400"),
            },
            {
                "kind": "APORTE",
                "quantity": Decimal("10"),
                "price": Decimal("60"),
                "fees": Decimal("0"),
                "amount": Decimal("600"),
            },
        ]
    )
    assert p["average_price"] == Decimal("50")
    assert p["invested"] == Decimal("1000")


def test_resgate_reduz_qtd_mantem_medio():
    p = position(
        [
            {
                "kind": "APORTE",
                "quantity": Decimal("10"),
                "price": Decimal("40"),
                "fees": Decimal("0"),
                "amount": Decimal("400"),
            },
            {
                "kind": "RESGATE",
                "quantity": Decimal("4"),
                "price": Decimal("50"),
                "fees": Decimal("0"),
                "amount": Decimal("200"),
            },
        ]
    )
    assert p["quantity"] == Decimal("6")
    assert p["average_price"] == Decimal("40")
    assert p["invested"] == Decimal("240")
    assert p["resgates"] == Decimal("200")


def test_rendimento_nao_mexe_posicao():
    p = position(
        [
            {
                "kind": "APORTE",
                "quantity": Decimal("10"),
                "price": Decimal("40"),
                "fees": Decimal("0"),
                "amount": Decimal("400"),
            },
            {"kind": "RENDIMENTO", "quantity": None, "price": None, "fees": Decimal("0"), "amount": Decimal("25")},
        ]
    )
    assert p["quantity"] == Decimal("10") and p["rendimentos"] == Decimal("25")


def _op(kind, qty, price="0", fees="0", amount="0"):
    return {
        "kind": kind,
        "quantity": Decimal(qty),
        "price": Decimal(price),
        "fees": Decimal(fees),
        "amount": Decimal(amount),
    }


def test_resgate_parcial_aporte_posterior():
    # 100@10, vende 50, compra 50@20 → base cai para 500 e volta a 1500/100 = 15
    p = position(
        [
            _op("APORTE", "100", "10", "0", "1000"),
            _op("RESGATE", "50", "12", "0", "600"),
            _op("APORTE", "50", "20", "0", "1000"),
        ]
    )
    assert p["quantity"] == Decimal("100")
    assert p["average_price"] == Decimal("15")
    assert p["invested"] == Decimal("1500")
    assert p["aportes"] == Decimal("2000") and p["resgates"] == Decimal("600")


def test_resgate_total_zera_base():
    p = position(
        [
            _op("APORTE", "10", "40", "0", "400"),
            _op("RESGATE", "10", "50", "0", "500"),
            _op("APORTE", "5", "20", "0", "100"),
        ]
    )
    assert p["quantity"] == Decimal("5")
    assert p["average_price"] == Decimal("20")
    assert p["invested"] == Decimal("100")


def test_resgate_sem_arredondamento_intermediario():
    # custo unitário 10/3 = 3.333...: vende 1 → base 20/3, médio exibido 3.33
    p = position([_op("APORTE", "3", "0", "0", "10"), _op("RESGATE", "1", "5", "0", "5")])
    assert p["quantity"] == Decimal("2")
    assert p["average_price"] == Decimal("3.33")
    assert p["invested"] == Decimal("6.66")


def test_resgate_acima_da_posicao_zera_base():
    # dado inconsistente (vende mais do que tem): base não pode ficar negativa
    p = position([_op("APORTE", "10", "40", "0", "400"), _op("RESGATE", "15", "50", "0", "750")])
    assert p["quantity"] == Decimal("-5")
    assert p["average_price"] == Decimal("0")
    assert p["invested"] == Decimal("0")


def test_reinvestimento_soma_custo_sem_receita():
    p = position(
        [
            _op("APORTE", "10", "100", "0", "1000"),
            _op("REINVESTIMENTO", "1", "100", "0", "100"),
        ]
    )
    assert p["quantity"] == Decimal("11")
    assert p["average_price"] == Decimal("100")
    assert p["invested"] == Decimal("1100")
    assert p["aportes"] == Decimal("1000") and p["reinvestimentos"] == Decimal("100")
    assert p["rendimentos"] == Decimal("0")


def test_vazio():
    p = position([])
    assert p["quantity"] == 0 and p["average_price"] == 0 and p["invested"] == 0
