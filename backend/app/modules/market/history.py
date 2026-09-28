"""Histórico da brapi (7.3): série diária p/ benchmarks e TWR."""

import httpx
from datetime import date, datetime

from app.core.config import settings
from app.modules.market.brapi import BrapiError, _headers, _raise_for_status


async def history(symbol: str, start: date, end: date, token: str | None = None,
                  client: httpx.AsyncClient | None = None) -> list[dict]:
    """Retorna [{date, close}] com adjustedClose ascendente."""
    from app.modules.market.brapi import BrapiAuthError

    tok = token or settings.brapi_token
    if not tok:
        raise BrapiAuthError("BRAPI_TOKEN não configurado")
    own = client is None
    client = client or httpx.AsyncClient(timeout=settings.brapi_timeout_s)
    try:
        res = await client.get(
            f"{settings.brapi_base_url}/v2/stocks/historical",
            params={"symbols": symbol.strip().upper(), "interval": "1d",
                    "startDate": start.isoformat(), "endDate": end.isoformat(),
                    "sortOrder": "asc"},
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
        results = res.json().get("results") or []
    except ValueError:
        raise BrapiError("Resposta não-JSON da brapi")
    if not results:
        raise BrapiError(f"Sem histórico para {symbol}")
    out = []
    for p in (results[0].get("data") or {}).get("historicalDataPrice") or []:
        if p.get("adjustedClose") is None:
            continue
        out.append({"date": datetime.fromtimestamp(p["date"]).date(), "close": float(p["adjustedClose"])})
    return out
