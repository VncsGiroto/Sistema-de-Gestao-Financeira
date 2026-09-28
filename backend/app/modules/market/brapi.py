"""Cliente da brapi (7.2a): cotação de ativos brasileiros.

Token lido do ambiente (BRAPI_TOKEN) — nunca do frontend, nunca commitado.
Testes usam httpx.MockTransport: CI nunca bate na API real.
"""

from datetime import datetime

import httpx
from pydantic import BaseModel

from app.core.config import settings


class BrapiError(Exception):
    pass


class BrapiAuthError(BrapiError):
    """401: token ausente/inválido."""


class BrapiForbiddenError(BrapiError):
    """403: plano não cobre o dado."""


class BrapiRateLimitedError(BrapiError):
    def __init__(self, message: str, retry_after_s: int = 60):
        super().__init__(message)
        self.retry_after_s = retry_after_s


class QuoteData(BaseModel):
    symbol: str
    short_name: str | None = None
    currency: str = "BRL"
    price: float
    change: float | None = None
    change_percent: float | None = None
    volume: int | None = None
    market_time: datetime | None = None


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _raise_for_status(res: httpx.Response) -> None:
    if res.status_code < 400:
        return
    if res.status_code == 401:
        raise BrapiAuthError("BRAPI_TOKEN ausente ou inválido")
    if res.status_code == 403:
        raise BrapiForbiddenError("Plano brapi não cobre este dado")
    if res.status_code == 429:
        try:
            retry = int(res.headers.get("Retry-After", "60"))
        except ValueError:
            retry = 60
        raise BrapiRateLimitedError("Cota brapi esgotada", retry_after_s=retry)
    raise BrapiError(f"brapi respondeu {res.status_code}")


def _parse_quote(symbol: str, payload: dict) -> QuoteData:
    results = payload.get("results") or []
    if not results:
        raise BrapiError(f"Sem cotação para {symbol}")
    d = results[0].get("data") or {}
    if d.get("regularMarketPrice") is None:
        raise BrapiError(f"Sem preço para {symbol}")
    mt = d.get("regularMarketTime")
    return QuoteData(
        symbol=results[0].get("symbol") or symbol.upper(),
        short_name=d.get("shortName"),
        currency=d.get("currency") or "BRL",
        price=float(d["regularMarketPrice"]),
        change=d.get("regularMarketChange"),
        change_percent=d.get("regularMarketChangePercent"),
        volume=d.get("regularMarketVolume"),
        market_time=datetime.fromisoformat(mt.replace("Z", "+00:00")) if mt else None,
    )


async def get_quote(symbol: str, token: str | None = None, client: httpx.AsyncClient | None = None) -> QuoteData:
    """Busca a cotação e retorna `results[0].data` tipado."""
    tok = token or settings.brapi_token
    if not tok:
        raise BrapiAuthError("BRAPI_TOKEN não configurado")
    sym = symbol.strip().upper()
    own = client is None
    client = client or httpx.AsyncClient(timeout=settings.brapi_timeout_s)
    try:
        res = await client.get(
            f"{settings.brapi_base_url}/v2/stocks/quote",
            params={"symbols": sym},
            headers=_headers(tok),
        )
    except httpx.TimeoutException as e:
        raise BrapiError(f"Timeout na brapi: {e}")
    except httpx.HTTPError as e:
        raise BrapiError(f"Falha de rede na brapi: {e}")
    finally:
        if own:
            await client.aclose()
    _raise_for_status(res)
    try:
        payload = res.json()
    except ValueError:
        raise BrapiError("Resposta não-JSON da brapi")
    return _parse_quote(sym, payload)
