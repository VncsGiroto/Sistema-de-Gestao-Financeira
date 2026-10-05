from datetime import datetime

from pydantic import BaseModel, Field


class ImportOut(BaseModel):
    id: int
    account_id: int
    source: str
    file_name: str
    status: str
    total_rows: int
    imported_rows: int
    duplicate_rows: int
    error: str | None
    created_at: datetime
    processed_at: datetime | None


class ImportItemOut(BaseModel):
    id: int
    row_no: int
    verdict: str
    payload: dict
    matched_transaction_id: int | None = None
    decision: str | None = None


class DecisionIn(BaseModel):
    item_id: int
    decision: str = Field(pattern="^(KEEP_BOTH|DISCARD_IMPORTED)$")


class ReviewIn(BaseModel):
    decisions: list[DecisionIn] = Field(min_length=1)


class CommitOut(BaseModel):
    imported_rows: int
    duplicate_rows: int
    skipped: int
