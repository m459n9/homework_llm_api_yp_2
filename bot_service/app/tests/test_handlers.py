from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from app.core.config import settings


def _make_token(sub: str = "1", role: str = "user") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=60),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def _make_message(text: str, user_id: int = 123, chat_id: int = 456) -> MagicMock:
    message = AsyncMock()
    message.text = text
    message.from_user = MagicMock()
    message.from_user.id = user_id
    message.chat = MagicMock()
    message.chat.id = chat_id
    message.answer = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_cmd_token_saves_to_redis(fake_redis):
    token = _make_token(sub="42")
    msg = _make_message(f"/token {token}")

    with patch("app.bot.handlers.get_redis", return_value=fake_redis):
        from app.bot.handlers import cmd_token
        await cmd_token(msg)

    stored = await fake_redis.get("token:123")
    assert stored == token
    msg.answer.assert_called_once()
    assert "принят" in msg.answer.call_args[0][0].lower() or "сохранён" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_token_rejects_invalid(fake_redis):
    msg = _make_message("/token invalidtoken")

    with patch("app.bot.handlers.get_redis", return_value=fake_redis):
        from app.bot.handlers import cmd_token
        await cmd_token(msg)

    stored = await fake_redis.get("token:123")
    assert stored is None
    msg.answer.assert_called_once()


@pytest.mark.asyncio
async def test_handle_text_no_token(fake_redis):
    msg = _make_message("Hello LLM")

    with patch("app.bot.handlers.get_redis", return_value=fake_redis):
        from app.bot.handlers import handle_text
        await handle_text(msg)

    msg.answer.assert_called_once()
    assert "токен" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_handle_text_with_valid_token(fake_redis):
    token = _make_token(sub="42")
    await fake_redis.set("token:123", token)

    msg = _make_message("Hello LLM")

    with (
        patch("app.bot.handlers.get_redis", return_value=fake_redis),
        patch("app.bot.handlers.llm_request") as mock_task,
    ):
        mock_task.delay = MagicMock()
        from app.bot.handlers import handle_text
        await handle_text(msg)

    mock_task.delay.assert_called_once_with(456, "Hello LLM")
    msg.answer.assert_called_once()
    assert "принят" in msg.answer.call_args[0][0].lower()
