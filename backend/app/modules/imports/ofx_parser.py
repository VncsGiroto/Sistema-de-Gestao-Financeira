"""Parse OFX 1.x (SGML) e 2.x (XML) via ofxparse. Puro e síncrono (roda em BackgroundTask)."""

import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation


class OfxParseError(ValueError):
    pass


@dataclass
class RawTx:
    fitid: str | None
    date: date | None
    amount: Decimal | None
    memo: str
    name: str
    trntype: str


def _to_decimal(value) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


# Valores de ENCODING fora do padrão que alguns bancos emitem (ex.: C6: "UTF - 8")
_ENCODING_ALIASES = {
    "UTF - 8": "UTF-8",
    "UTF8": "UTF-8",
    "UTF_8": "UTF-8",
    "ISO - 8859 - 1": "1252",
    "ISO-8859-1": "1252",
}

_FALLBACK_HEADERS = (
    "OFXHEADER:100\r\nDATA:OFXSGML\r\nVERSION:102\r\nSECURITY:NONE\r\n"
    "ENCODING:USASCII\r\nCHARSET:1252\r\nCOMPRESSION:NONE\r\n"
    "OLDFILEUID:NONE\r\nNEWFILEUID:NONE\r\n\r\n"
)


def normalize_headers(raw: bytes) -> bytes:
    """Tolera headers fora do padrão (espaços, ENCODING exótico, BOM/CRLF).

    Só toca o bloco de headers (até a primeira linha em branco ou `<OFX`);
    o corpo SGML/XML vai intacto para o ofxparse.
    """
    text = raw.decode("utf-8-sig", errors="replace").lstrip("\ufeff")
    lines = text.splitlines()
    head: list[str] = []
    body_at = len(lines)
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.upper().startswith("<OFX") or s.startswith("<?xml"):
            body_at = i
            break
        if ":" not in s or len(head) >= 12:
            body_at = i
            break
        key, _, value = s.partition(":")
        key, value = key.strip().upper(), value.strip()
        if key == "ENCODING":
            value = _ENCODING_ALIASES.get(value.upper(), value)
        head.append(f"{key}:{value}")
    body = "\n".join(lines[body_at:])
    return ("\n".join(head) + "\n\n" + body).encode("utf-8")


def _strip_headers(raw: bytes) -> bytes:
    """Devolve só o corpo (a partir de `<OFX` ou `<?xml`) para a tentativa com headers padrão."""
    text = raw.decode("utf-8-sig", errors="replace").lstrip("\ufeff")
    upper = text.upper()
    for marker in ("<OFX", "<?XML"):
        at = upper.find(marker)
        if at != -1:
            return text[at:].encode("utf-8")
    return text.encode("utf-8")


def _try_parse(raw: bytes):
    from ofxparse import OfxParser

    return OfxParser.parse(io.BytesIO(raw))


def parse_ofx(raw: bytes) -> list[RawTx]:
    if not raw or not raw.strip():
        raise OfxParseError("Arquivo vazio")
    try:
        from ofxparse import OfxParser  # noqa: F401 (import valida disponibilidade)
    except ImportError as e:
        raise OfxParseError(f"Biblioteca OFX indisponível: {e}")
    last_error: Exception | None = None
    for attempt in (normalize_headers(raw), _FALLBACK_HEADERS.encode() + _strip_headers(raw)):
        try:
            ofx = _try_parse(attempt)
            break
        except Exception as e:
            last_error = e
    else:
        raise OfxParseError(f"OFX inválido: {last_error}")
    if ofx.account is None or not ofx.account.statement:
        raise OfxParseError("Nenhum extrato encontrado no arquivo")
    out: list[RawTx] = []
    statements = [ofx.account.statement] if not isinstance(ofx.account.statement, list) else ofx.account.statement
    for stmt in statements:
        for t in stmt.transactions or []:
            d = t.date.date() if getattr(t, "date", None) else None
            out.append(RawTx(
                fitid=(str(t.id).strip() if getattr(t, "id", None) else None) or None,
                date=d,
                amount=_to_decimal(getattr(t, "amount", None)),
                memo=str(getattr(t, "memo", "") or ""),
                name=str(getattr(t, "payee", "") or ""),
                trntype=str(getattr(t, "type", "") or "").upper(),
            ))
    return out
