import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings


def _now() -> datetime:
    return datetime.now(UTC)


def create_access_token(user_id: int) -> tuple[str, int]:
    exp = _now() + timedelta(seconds=settings.access_ttl)
    payload = {"sub": str(user_id), "type": "access", "exp": exp, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg), settings.access_ttl


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    exp = _now() + timedelta(seconds=settings.refresh_ttl)
    raw = f"{user_id}.{uuid.uuid4().hex}.{exp.timestamp()}"
    token = jwt.encode(
        {"sub": str(user_id), "type": "refresh", "exp": exp, "jti": uuid.uuid4().hex},
        settings.jwt_secret,
        algorithm=settings.jwt_alg,
    )
    token_hash = hashlib.sha256(f"{raw}.{token}".encode()).hexdigest()
    return token, token_hash, exp


def decode_token(token: str, expected_type: str) -> int:
    return decode_claims(token, expected_type)["sub"]


def decode_claims(token: str, expected_type: str) -> dict:
    """Valida e devolve {sub: int, jti: str} (jti alimenta a deny-list)."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expirado")
    except jwt.InvalidTokenError:
        raise ValueError("Token inválido")
    if payload.get("type") != expected_type:
        raise ValueError("Tipo de token inválido")
    if not payload.get("jti"):
        raise ValueError("Token sem identificador")
    return {"sub": int(payload["sub"]), "jti": str(payload["jti"])}


RECOVERY_TTL_SECONDS = 3600


def create_recovery_token(user_id: int) -> tuple[str, datetime]:
    exp = _now() + timedelta(seconds=RECOVERY_TTL_SECONDS)
    token = jwt.encode(
        {"sub": str(user_id), "type": "recovery", "exp": exp, "jti": uuid.uuid4().hex},
        settings.jwt_secret,
        algorithm=settings.jwt_alg,
    )
    return token, exp


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
