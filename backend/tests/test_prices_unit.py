"""7.2b unit: accrual, BCB parse (mock), rateio (puros, sem DB/rede real)."""

from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.modules.investments import returns as ret
from app.modules.market import accrual as acc
from app.modules.market import bcb


def test_business_days():
    days = acc.business_days(date(2026, 9, 25), date(2026, 9, 30))  # sex..ter
    assert days == [date(2026, 9, 25), date(2026, 9, 28), date(2026, 9, 29)]
    assert acc.business_days(date(2026, 9, 26), date(2026, 9, 26)) == []


def test_cdi_factor():
    cdi = {date(2026, 9, 25): Decimal("0.05"), date(2026, 9, 28): Decimal("0.05")}
    f = acc.cdi_factor(Decimal("100"), [date(2026, 9, 25), date(2026, 9, 28)], cdi)
    assert f == (Decimal("1.0005") ** 2)
    # dia sem cotação = fator neutro
    assert acc.cdi_factor(Decimal("110"), [date(2026, 9, 27)], {}) == Decimal("1")


def test_prefixado_factor():
    assert acc.prefixado_factor(Decimal("12"), 252) == Decimal("1.12")
    assert acc.prefixado_factor(Decimal("12"), 0) == Decimal("1")


def test_accrue_lots_fifo_consumo():
    lots = [
        {"qty": Decimal("100"), "price": Decimal("10"), "date": date(2026, 1, 5)},
        {"qty": Decimal("50"), "price": Decimal("12"), "date": date(2026, 2, 5)},
    ]
    rest = acc.consume_fifo(lots, Decimal("120"))
    assert rest == [{"qty": Decimal("30"), "price": Decimal("12"), "date": date(2026, 2, 5)}]
    with pytest.raises(ValueError):
        acc.consume_fifo(lots, Decimal("999"))


def test_accrue_prefixado_valor():
    lots = [{"qty": Decimal("100"), "price": Decimal("10"), "date": date(2026, 9, 25)}]
    v = acc.accrue_lots(lots, "PREFIXADO", Decimal("12"), date(2026, 9, 30), {})
    # 3 du (25, 28, 29): 1000 * 1.12^(3/252)
    assert v == Decimal("1000") * (Decimal("1.12") ** (Decimal("3") / Decimal("252")))


def test_accrue_tipo_nao_suportado():
    with pytest.raises(ValueError):
        acc.accrue_lots(
            [{"qty": Decimal("1"), "price": Decimal("1"), "date": date(2026, 9, 25)}],
            "IPCA_MAIS",
            Decimal("6"),
            date(2026, 9, 30),
            {},
        )


async def test_bcb_parse_mock():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "bcdata.sgs.12" in str(request.url)
        assert request.url.params["formato"] == "json"
        return httpx.Response(
            200,
            json=[
                {"data": "25/09/2026", "valor": "0.0527"},
                {"data": "lixo", "valor": "x"},  # linha ruim é ignorada
            ],
        )

    series = await bcb.cdi_range(
        date(2026, 9, 25), date(2026, 9, 28), client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    assert series == {date(2026, 9, 25): Decimal("0.0527")}


async def test_bcb_erro_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    with pytest.raises(bcb.BcbError):
        await bcb.cdi_range(
            date(2026, 9, 25), date(2026, 9, 25), client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        )


async def test_bcb_range_invertido():
    assert await bcb.cdi_range(date(2026, 9, 28), date(2026, 9, 25)) == {}


def test_xirr_caso_conhecido():
    r = ret.xirr([(date(2025, 1, 1), Decimal("-1000")), (date(2026, 1, 1), Decimal("1100"))])
    assert r is not None and abs(r - Decimal("0.1")) < Decimal("0.0001")


def test_xirr_sem_troca_de_sinal():
    assert ret.xirr([(date(2025, 1, 1), Decimal("-1000"))]) is None
    assert ret.xirr([(date(2025, 1, 1), Decimal("-100")), (date(2026, 1, 1), Decimal("-50"))]) is None


def test_twr_cotas():
    evs = [
        {"date": date(2026, 1, 1), "flow": Decimal("1000"), "value": Decimal("0")},
        {"date": date(2026, 7, 1), "flow": Decimal("500"), "value": Decimal("1100")},
        {"date": date(2026, 12, 31), "flow": Decimal("0"), "value": Decimal("1870")},
    ]
    # 1000 cotas; cota=1.1 em jul → +500/1.1 cotas; final 1870/1454.54 = 1.2857 → 28.57%
    r = ret.unitize(evs)
    assert r is not None and abs(r - Decimal("0.2857")) < Decimal("0.001")
    assert ret.annualize(r, 364) is not None


def test_twr_sem_eventos():
    assert ret.unitize([]) is None
    assert ret.annualize(Decimal("0.1"), 0) is None
