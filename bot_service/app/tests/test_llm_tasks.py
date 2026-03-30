import json

import httpx
import respx

from app.core.config import settings
from app.tasks.llm_tasks import LLM_FAILURE_MESSAGE, llm_request


@respx.mock
def test_llm_request_uses_openrouter_and_sends_telegram(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")

    openrouter_route = respx.post(
        f"{settings.OPENROUTER_BASE_URL}/chat/completions"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "LLM answer"}}]},
        )
    )
    telegram_route = respx.post(
        "https://api.telegram.org/bottest-token/sendMessage"
    ).mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    result = llm_request(456, "Hello LLM")

    assert result == "LLM answer"
    assert openrouter_route.called
    assert telegram_route.called
    assert json.loads(telegram_route.calls[0].request.content) == {
        "chat_id": 456,
        "text": "LLM answer",
    }


@respx.mock
def test_llm_request_sends_fallback_when_openrouter_fails(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")

    respx.post(f"{settings.OPENROUTER_BASE_URL}/chat/completions").mock(
        side_effect=httpx.ConnectError("network down")
    )
    telegram_route = respx.post(
        "https://api.telegram.org/bottest-token/sendMessage"
    ).mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {}})
    )

    result = llm_request(456, "Hello LLM")

    assert result == LLM_FAILURE_MESSAGE
    assert telegram_route.called
    assert json.loads(telegram_route.calls[0].request.content) == {
        "chat_id": 456,
        "text": LLM_FAILURE_MESSAGE,
    }
