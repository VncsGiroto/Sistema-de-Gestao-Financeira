"""7.2a unit: cliente brapi com httpx.MockTransport (CI nunca bate na API real)."""

import httpx
import pytest

from app.modules.market import brapi
from app.modules.market.brapi import (
    BrapiAuthError,
    BrapiError,
    BrapiForbiddenError,
    BrapiRateLimitedError,
    get_quote,
)

BODY = {
    "results": [
        {
            "requestedSymbol": "B3SA3",
            "symbol": "B3SA3",
            "data": {
                "shortName": "B3 ON",
                "currency": "BRL",
                "regularMarketPrice": 12.34,
                "regularMarketChange": 0.12,
                "regularMarketChangePercent": 0.98,
                "regularMarketVolume": 1000,
                "regularMarketTime": "2026-09-28T17:08:02.000Z",
            },
        }
    ]
}


def _client(status: int = 200, json=None, headers=None) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer tok-test"
        assert request.url.params["symbols"] == "B3SA3"
        assert str(request.url).startswith("https://brapi.dev/api/v2/stocks/quote")
        return httpx.Response(status, json=json, headers=headers or {})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_quote_ok():
    q = await get_quote("b3sa3", token="tok-test", client=_client(json=BODY))
    assert q.symbol == "B3SA3" and q.price == 12.34 and q.currency == "BRL"
    assert q.short_name == "B3 ON" and q.volume == 1000
    assert q.market_time is not None


async def test_sem_token():
    with pytest.raises(BrapiAuthError):
        await get_quote("B3SA3", token="", client=_client(json=BODY))


async def test_401_403_429():
    with pytest.raises(BrapiAuthError):
        await get_quote("B3SA3", token="tok-test", client=_client(401, {"error": "x"}))
    with pytest.raises(BrapiForbiddenError):
        await get_quote("B3SA3", token="tok-test", client=_client(403, {"error": "x"}))
    try:
        await get_quote("B3SA3", token="tok-test",
                        client=_client(429, {"error": "x"}, {"Retry-After": "120"}))
        raise AssertionError("deveria levantar")
    except BrapiRateLimitedError as e:
        assert e.retry_after_s == 120


async def test_500_e_sem_resultados():
    with pytest.raises(BrapiError):
        await get_quote("B3SA3", token="tok-test", client=_client(500, {"error": "x"}))
    with pytest.raises(BrapiError):
        await get_quote("B3SA3", token="tok-test", client=_client(json={"results": []}))
    with pytest.raises(BrapiError):
        await get_quote("B3SA3", token="tok-test",
                        client=_client(json={"results": [{"symbol": "B3SA3", "data": {}}]}))
