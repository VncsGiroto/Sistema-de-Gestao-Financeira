"""0018 unit: estimativa do líquido de resgate (IR estimado; puro, sem DB)."""

from decimal import Decimal

from app.modules.investments.taxation import auto_rate, estimate_net


def test_rf_regressiva_por_prazo():
    assert auto_rate("RENDA_FIXA", 30) == Decimal("22.5")
    assert auto_rate("RENDA_FIXA", 180) == Decimal("22.5")
    assert auto_rate("RENDA_FIXA", 181) == Decimal("20")
    assert auto_rate("RENDA_FIXA", 400) == Decimal("17.5")
    assert auto_rate("RENDA_FIXA", 721) == Decimal("15")
    assert auto_rate("RENDA_FIXA", None) == Decimal("22.5")  # prazo desconhecido: conservador


def test_outras_classes_15():
    for cls in ("RENDA_VARIAVEL", "FUNDOS", "CRIPTO", "OUTROS"):
        assert auto_rate(cls, 10) == Decimal("15")


def test_lucro_aplica_ir():
    est = estimate_net(
        current_value=Decimal("1100.00"),
        invested=Decimal("1000.00"),
        days_held=400,
        asset_class="RENDA_FIXA",
        tax_rate=None,
    )
    assert est["gross"] == Decimal("1100.00") and est["gain"] == Decimal("100.00")
    assert est["rate"] == Decimal("17.5") and est["rate_source"] == "auto"
    assert est["tax"] == Decimal("17.50") and est["net"] == Decimal("1082.50")


def test_manual_sobrescreve_auto():
    est = estimate_net(
        current_value=Decimal("1100.00"),
        invested=Decimal("1000.00"),
        days_held=10,
        asset_class="RENDA_VARIAVEL",
        tax_rate=Decimal("10.00"),
    )
    assert est["rate"] == Decimal("10.00") and est["rate_source"] == "manual"
    assert est["tax"] == Decimal("10.00") and est["net"] == Decimal("1090.00")


def test_sem_lucro_sem_ir():
    est = estimate_net(
        current_value=Decimal("900.00"),
        invested=Decimal("1000.00"),
        days_held=10,
        asset_class="RENDA_VARIAVEL",
        tax_rate=None,
    )
    assert est["tax"] == Decimal("0.00") and est["net"] == Decimal("900.00")


def test_sem_preco_sem_estimativa():
    est = estimate_net(
        current_value=None, invested=Decimal("1000.00"), days_held=10, asset_class="RENDA_VARIAVEL", tax_rate=None
    )
    assert est["net"] is None and est["tax"] is None
    assert est["rate"] == Decimal("15") and est["rate_source"] == "auto"
