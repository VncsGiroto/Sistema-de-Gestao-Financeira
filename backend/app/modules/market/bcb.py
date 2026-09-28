"""BCB SGS: CDI diário (série 12, sem chave). Usado no accrual de RF."""

import httpx
from datetime import date
from decimal import Decimal, InvalidOperation


class BcbError(Exception):
    pass


def _br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _parse(rows: list) -> dict:
    out = {}
    for r in rows:
        try:
            d = date(int(r["data"][6:10]), int(r["data"][3:5]), int(r["data"][0:2]))
            out[d] = Decimal(str(r["valor"]).replace(",", "."))
        except (KeyError, ValueError, InvalidOperation, IndexError):
            continue
    return out


async def cdi_range(start: date, end: date, timeout_s: int = 15,
                    client: httpx.AsyncClient | None = None) -> dict:
    """Retorna {date: taxa % a.d.} do CDI no intervalo (inclusive)."""
    return await series("12", start, end, timeout_s, client)


async def series(code: str, start: date, end: date, timeout_s: int = 15,
                 client: httpx.AsyncClient | None = None) -> dict:
    """Série genérica do BCB SGS {date: valor}. code ex.: '12' (CDI), '433' (IPCA mensal)."""
    if start > end:
        return {}
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
    params = {"formato": "json", "dataInicial": _br(start), "dataFinal": _br(end)}
    own = client is None
    client = client or httpx.AsyncClient(timeout=timeout_s)
    try:
        res = await client.get(url, params=params)
    except httpx.TimeoutException as e:
        raise BcbError(f"Timeout no BCB: {e}")
    except httpx.HTTPError as e:
        raise BcbError(f"Falha de rede no BCB: {e}")
    finally:
        if own:
            await client.aclose()
    if res.status_code != 200:
        raise BcbError(f"BCB respondeu {res.status_code}")
    try:
        return _parse(res.json())
    except ValueError:
        raise BcbError("Resposta não-JSON do BCB")
