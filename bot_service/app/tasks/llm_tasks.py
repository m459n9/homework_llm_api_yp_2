import asyncio
import logging

import httpx

from app.core.config import settings
from app.infra.celery_app import celery_app
from app.services.openrouter_client import OpenRouterError, call_openrouter

logger = logging.getLogger(__name__)
LLM_FAILURE_MESSAGE = "Сервис LLM временно недоступен. Попробуйте позже."
TELEGRAM_MESSAGE_LIMIT = 4000


@celery_app.task(name="llm_request")
def llm_request(tg_chat_id: int, prompt: str) -> str:
    return asyncio.run(_run_llm_request(tg_chat_id, prompt))


async def _run_llm_request(tg_chat_id: int, prompt: str) -> str:
    try:
        answer = await call_openrouter(prompt)
    except OpenRouterError:
        logger.exception("OpenRouter request failed for chat_id=%s", tg_chat_id)
        answer = LLM_FAILURE_MESSAGE

    try:
        await _send_telegram_message(tg_chat_id, answer)
    except httpx.HTTPError:
        logger.exception("Telegram delivery failed for chat_id=%s", tg_chat_id)
        raise

    return answer


async def _send_telegram_message(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = [text[i:i + TELEGRAM_MESSAGE_LIMIT] for i in range(0, len(text), TELEGRAM_MESSAGE_LIMIT)] or [""]
    async with httpx.AsyncClient(timeout=30.0) as client:
        for chunk in chunks:
            response = await client.post(url, json={"chat_id": chat_id, "text": chunk})
            response.raise_for_status()
