import pytest
import respx
import httpx

from app.core.config import settings
from app.services.openrouter_client import OpenRouterError, call_openrouter


@pytest.mark.asyncio
@respx.mock
async def test_call_openrouter_success():
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": "Hello! I am an AI assistant."
                }
            }
        ]
    }

    respx.post(f"{settings.OPENROUTER_BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result = await call_openrouter("Hi there")
    assert result == "Hello! I am an AI assistant."


@pytest.mark.asyncio
@respx.mock
async def test_call_openrouter_error():
    respx.post(f"{settings.OPENROUTER_BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "Internal Server Error"})
    )

    with pytest.raises(OpenRouterError, match="OpenRouter request failed"):
        await call_openrouter("Hi there")


@pytest.mark.asyncio
@respx.mock
async def test_call_openrouter_malformed_response():
    respx.post(f"{settings.OPENROUTER_BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": []})
    )

    with pytest.raises(OpenRouterError, match="Malformed OpenRouter response"):
        await call_openrouter("Hi there")
