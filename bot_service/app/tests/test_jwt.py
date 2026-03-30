from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.core.jwt import decode_and_validate


def _make_token(sub: str = "1", role: str = "user", exp_minutes: int = 60) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=exp_minutes),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def test_decode_valid_token():
    token = _make_token(sub="42", role="user")
    payload = decode_and_validate(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "user"


def test_decode_invalid_token():
    with pytest.raises(ValueError):
        decode_and_validate("garbage.token.string")


def test_decode_expired_token():
    token = _make_token(exp_minutes=-1)
    with pytest.raises(ValueError):
        decode_and_validate(token)


def test_decode_wrong_secret():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": "1", "exp": now + timedelta(hours=1)},
        "wrong_secret",
        algorithm="HS256",
    )
    with pytest.raises(ValueError):
        decode_and_validate(token)
