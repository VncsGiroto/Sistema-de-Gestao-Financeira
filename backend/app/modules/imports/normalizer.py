"""Normalização para o formato interno (OFX-IMPORT.md §2)."""

import hashlib
import re
import unicodedata
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.modules.imports.ofx_parser import RawTx


class NormalizedTx(BaseModel):
    date: date
    description: str
    amount: Decimal
    type: str  # INCOME | EXPENSE
    account_id: int
    source: str
    external_id: str


def clean_description(value: str) -> str:
    v = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    v = re.sub(r"[^A-Z0-9 ]", " ", v.upper())
    return re.sub(r"\s+", " ", v).strip()


def stable_external_id(date_: date, amount: Decimal, memo: str) -> str:
    return hashlib.sha256(f"{date_.isoformat()}|{amount}|{memo}".encode()).hexdigest()[:32]


def normalize(raw: RawTx, account_id: int, source: str = "OFX") -> NormalizedTx | None:
    """Retorna None quando a linha é inválida (amount zero/ausente ou sem data)."""
    if raw.amount is None or raw.amount == 0 or raw.date is None:
        return None
    original = f"{raw.name} {raw.memo}".strip()
    return NormalizedTx(
        date=raw.date,
        description=clean_description(original) or "SEM DESCRICAO",
        amount=raw.amount,
        type="INCOME" if raw.amount > 0 else "EXPENSE",
        account_id=account_id,
        source=source,
        external_id=(raw.fitid.strip() if raw.fitid else None) or stable_external_id(raw.date, raw.amount, original),
    )


class BaseImporter(ABC):
    """O (aberto/fechado): novas fontes implementam sem alterar o pipeline."""

    source: str

    @abstractmethod
    def parse(self, raw: bytes) -> list[RawTx]: ...

    def normalize(self, raw: RawTx, account_id: int) -> NormalizedTx | None:
        return normalize(raw, account_id, self.source)


class OfxImporter(BaseImporter):
    source = "OFX"

    def parse(self, raw: bytes) -> list[RawTx]:
        from app.modules.imports.ofx_parser import parse_ofx

        return parse_ofx(raw)
