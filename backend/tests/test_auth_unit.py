import time

import jwt as pyjwt

from app.core.config import settings
from app.modules.auth import tokens
from app.modules.users.passwords import hash_password, verify_password


def test_password_roundtrip():
    h = hash_password("segredo-123")
    assert verify_password("segredo-123", h)
    assert not verify_password("errada", h)


def test_access_token_type_enforced():
    access, ttl = tokens.create_access_token(42)
    assert ttl == settings.access_ttl
    assert tokens.decode_token(access, "access") == 42
    try:
        tokens.decode_token(access, "refresh")
        raise AssertionError("deveria falhar tipo")
    except ValueError:
        pass


def test_access_token_expiry_claim():
    access, _ = tokens.create_access_token(7)
    payload = pyjwt.decode(access, settings.jwt_secret, algorithms=[settings.jwt_alg])
    assert payload["sub"] == "7"
    assert payload["type"] == "access"
    assert payload["exp"] - time.time() <= settings.access_ttl + 5


def test_refresh_token_hash_stable():
    _, h1, _ = tokens.create_refresh_token(1)
    assert len(h1) == 64


def test_recovery_token_type_and_ttl():
    token, exp = tokens.create_recovery_token(9)
    assert tokens.decode_token(token, "recovery") == 9
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    assert payload["type"] == "recovery"
    assert payload["exp"] - time.time() <= tokens.RECOVERY_TTL_SECONDS + 5
    try:
        tokens.decode_token(token, "refresh")
        raise AssertionError("deveria falhar tipo")
    except ValueError:
        pass
