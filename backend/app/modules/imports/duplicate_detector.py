"""Detecção de duplicidade (DEDUP.md). Puro, sem I/O — injetável e unit testável.

Nível 1 (exato): (user_id, source, external_id) já existe → EXACT_DUPLICATE.
Nível 2 (fuzzy): mesma conta, |Δdias| ≤ janela, amount igual no centavo,
Jaccard-trigram da descrição normalizada ≥ 0.70 → FUZZY_CANDIDATE + score.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

WINDOW_DAYS = 2
SIMILARITY_MIN = 0.70


def norm_description(value: str) -> str:
    v = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    v = v.upper()
    v = re.sub(r"\*\d+", " ", v)  # *1234 de maquininha
    v = re.sub(r"\b(LTDA|SA|S\.A\.?|MEI|ME|EPP|EIRELI)\b", " ", v)
    v = re.sub(r"[^A-Z0-9 ]", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def _trigrams(s: str) -> set[str]:
    s = f"  {s} "
    return {s[i : i + 3] for i in range(len(s) - 2)} if len(s) >= 3 else {s}


def similarity(a: str, b: str) -> float:
    ta, tb = _trigrams(norm_description(a)), _trigrams(norm_description(b))
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


@dataclass
class Candidate:
    id: int
    account_id: int
    date: date
    description: str
    amount: Decimal


def is_fuzzy(
    account_id: int,
    date_: date,
    description: str,
    amount: Decimal,
    other: Candidate,
    window_days: int = WINDOW_DAYS,
) -> tuple[bool, float]:
    if other.account_id != account_id:
        return False, 0.0
    if abs((date_ - other.date).days) > window_days:
        return False, 0.0
    if amount != other.amount:
        return False, 0.0
    score = similarity(description, other.description)
    return score >= SIMILARITY_MIN, round(score, 4)
