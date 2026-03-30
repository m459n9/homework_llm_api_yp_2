import httpx

from app.core.config import settings

REQUEST_TIMEOUT = 60.0


class OpenRouterError(RuntimeError):
    pass


async def call_openrouter(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                },
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "HTTP-Referer": settings.OPENROUTER_SITE_URL,
                    "X-Title": settings.OPENROUTER_APP_NAME,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OpenRouterError("OpenRouter request failed") from exc

    try:
        return response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterError("Malformed OpenRouter response") from exc
