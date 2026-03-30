from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_differs_from_plain():
    plain = "mysecretpassword"
    hashed = hash_password(plain)
    assert hashed != plain


def test_verify_password_correct():
    plain = "mysecretpassword"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_token():
    token = create_access_token(sub="42", role="user")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "user"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_invalid_token():
    try:
        decode_token("invalid.token.string")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
