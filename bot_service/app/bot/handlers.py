from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from app.core.jwt import decode_and_validate
from app.infra.redis import get_redis
from app.tasks.llm_tasks import llm_request

router = Router()


def _token_key(user_id: int) -> str:
    return f"token:{user_id}"


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать! Я LLM-консультант.\n\n"
        "Для начала работы авторизуйтесь через Auth Service "
        "(http://localhost:8000/docs) и отправьте мне токен командой:\n"
        "/token <ваш_jwt_токен>"
    )


@router.message(Command("token"))
async def cmd_token(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /token <ваш_jwt_токен>")
        return

    token = parts[1].strip()

    try:
        decode_and_validate(token)
    except ValueError:
        await message.answer("Невалидный или просроченный токен. Получите новый в Auth Service.")
        return

    redis = get_redis()
    await redis.set(_token_key(message.from_user.id), token)
    await message.answer("Токен принят и сохранён. Теперь вы можете отправлять запросы к LLM.")


@router.message(F.text)
async def handle_text(message: Message):
    redis = get_redis()
    token = await redis.get(_token_key(message.from_user.id))

    if not token:
        await message.answer(
            "У вас нет сохранённого токена. "
            "Авторизуйтесь через Auth Service и отправьте токен командой /token <jwt>"
        )
        return

    try:
        decode_and_validate(token)
    except ValueError:
        await redis.delete(_token_key(message.from_user.id))
        await message.answer(
            "Ваш токен истёк или невалиден. Получите новый в Auth Service и отправьте /token <jwt>"
        )
        return

    llm_request.delay(message.chat.id, message.text)
    await message.answer("Запрос принят. Ожидайте ответа от LLM...")
