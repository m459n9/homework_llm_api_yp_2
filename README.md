# Двухсервисная система LLM-консультаций

Распределённая система, состоящая из двух независимых сервисов: **Auth Service** (регистрация, логин, выдача JWT) и **Bot Service** (Telegram-бот с LLM-консультациями через Celery/RabbitMQ/Redis).

## Архитектура

```
┌────────────────────┐     JWT      ┌─────────────────────────────────────────┐
│                    │ ─────────►   │              Bot Service                │
│   Auth Service     │              │                                         │
│   (FastAPI)        │              │  ┌──────────┐     ┌──────────────────┐  │
│                    │              │  │ aiogram   │────►│   RabbitMQ       │  │
│  POST /auth/register              │  │ Telegram  │     │   (Celery broker)│  │
│  POST /auth/login  │              │  │ Bot       │     └────────┬─────────┘  │
│  GET  /auth/me     │              │  └──────────┘              │            │
│                    │              │       │                     ▼            │
│  SQLite + bcrypt   │              │       │             ┌──────────────┐     │
│  JWT (HS256)       │              │       │             │ Celery Worker│     │
└────────────────────┘              │       │             │ (OpenRouter) │     │
                                    │       │             └──────┬───────┘     │
                                    │       ▼                    │            │
                                    │  ┌──────────┐              │            │
                                    │  │  Redis    │◄─────────────┘            │
                                    │  │ (токены + │                           │
                                    │  │  backend) │                           │
                                    │  └──────────┘                           │
                                    └─────────────────────────────────────────┘
```

### Принцип разделения ответственности

| Компонент | Роль |
|-----------|------|
| **Auth Service** | Единственное место регистрации, логина и выпуска JWT. Не знает про Telegram. |
| **Bot Service** | Принимает сообщения в Telegram, валидирует JWT (не создаёт!), отправляет задачи в очередь. |
| **Celery Worker** | Обрабатывает LLM-запросы через OpenRouter, отправляет ответ пользователю. |
| **RabbitMQ** | Брокер задач Celery — обеспечивает асинхронную обработку. |
| **Redis** | Хранит JWT-токены по Telegram user_id + result backend Celery. |

## Структура проекта

```
├── docker-compose.yml
├── README.md
│
├── auth_service/
│   ├── Dockerfile
│   ├── .env
│   ├── pyproject.toml
│   ├── pytest.ini
│   └── app/
│       ├── main.py                    # FastAPI приложение, lifespan, /health
│       ├── core/
│       │   ├── config.py              # Настройки через pydantic-settings
│       │   ├── security.py            # bcrypt хеширование, JWT create/decode
│       │   └── exceptions.py          # HTTP-исключения (409, 401, 404, 403)
│       ├── db/
│       │   ├── base.py                # SQLAlchemy DeclarativeBase
│       │   ├── session.py             # Async engine + sessionmaker
│       │   └── models.py              # ORM-модель User
│       ├── schemas/
│       │   ├── auth.py                # RegisterRequest, TokenResponse
│       │   └── user.py                # UserPublic (без password_hash)
│       ├── repositories/
│       │   └── users.py               # CRUD: get_by_id, get_by_email, create
│       ├── usecases/
│       │   └── auth.py                # Бизнес-логика: register, login, me
│       ├── api/
│       │   ├── deps.py                # DI: get_db, get_current_user_id, OAuth2
│       │   ├── routes_auth.py         # Эндпоинты /auth/*
│       │   └── router.py              # Сборка роутеров
│       └── tests/
│           ├── conftest.py            # Временная SQLite БД, httpx ASGITransport
│           ├── test_security.py       # Unit: хеширование, JWT
│           └── test_integration.py    # Integration: HTTP-поток
│
└── bot_service/
    ├── Dockerfile
    ├── .env
    ├── pyproject.toml
    ├── pytest.ini
    └── app/
        ├── main.py                    # FastAPI /health (опционально)
        ├── run_bot.py                 # Точка входа: запуск polling
        ├── core/
        │   ├── config.py              # Настройки: BOT_TOKEN, JWT, Redis, RabbitMQ
        │   └── jwt.py                 # decode_and_validate (только проверка!)
        ├── infra/
        │   ├── redis.py               # get_redis() — клиент Redis
        │   └── celery_app.py          # Celery app с RabbitMQ broker
        ├── tasks/
        │   └── llm_tasks.py           # Celery-задача llm_request
        ├── services/
        │   └── openrouter_client.py   # httpx-клиент OpenRouter
        ├── bot/
        │   ├── dispatcher.py          # Bot + Dispatcher
        │   └── handlers.py            # /start, /token, обработка текста
        └── tests/
            ├── conftest.py            # Фикстура fakeredis
            ├── test_jwt.py            # Unit: валидация JWT
            ├── test_handlers.py       # Mock: handlers с fakeredis + mock Celery
            └── test_openrouter.py     # Integration: respx-мок OpenRouter
```

## Требования

- Python 3.11+
- Docker и Docker Compose
- [uv](https://docs.astral.sh/uv/) — пакетный менеджер

## Быстрый запуск

### 1. Настроить переменные окружения

**auth_service/.env** — обычно менять не нужно (по умолчанию SQLite + тестовый секрет):

```env
APP_NAME=auth-service
ENV=local
JWT_SECRET=change_me_super_secret
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
SQLITE_PATH=./auth.db
```

**bot_service/.env** — обязательно заполнить `TELEGRAM_BOT_TOKEN` и `OPENROUTER_API_KEY`:

```env
APP_NAME=bot-service
ENV=local
TELEGRAM_BOT_TOKEN=<ваш_токен_бота>
JWT_SECRET=change_me_super_secret
JWT_ALG=HS256
REDIS_URL=redis://redis:6379/0
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//
OPENROUTER_API_KEY=<ваш_api_key>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=stepfun/step-3.5-flash:free
OPENROUTER_SITE_URL=https://example.com
OPENROUTER_APP_NAME=bot-service
```

> **Важно:** `JWT_SECRET` должен совпадать в обоих сервисах.

### 2. Запустить через Docker Compose

```bash
docker compose up --build -d
```

Будут запущены 5 контейнеров:

| Сервис | Порт | Назначение |
|--------|------|------------|
| `auth_service` | `8000` | FastAPI + Swagger UI |
| `bot` | — | Telegram-бот (polling) |
| `celery_worker` | — | Обработка LLM-задач |
| `rabbitmq` | `5672`, `15672` | Брокер + Management UI |
| `redis` | `6379` | Хранилище токенов + backend |

### 3. Проверить, что всё поднялось

```bash
docker compose ps
```

Все 5 контейнеров должны иметь статус `Up`.

## Пользовательский сценарий

### Шаг 1: Регистрация в Auth Service

Открыть Swagger: **http://localhost:8000/docs**

Или через curl:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "surname@email.com", "password": "strongpass123"}'
```

Ответ:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Шаг 2: Логин (получение JWT)

```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=surname@email.com&password=strongpass123"
```

### Шаг 3: Проверка профиля

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <ваш_токен>"
```

Ответ:
```json
{
  "id": 1,
  "email": "surname@email.com",
  "role": "user",
  "created_at": "2026-03-22T22:09:07.703560"
}
```

### Шаг 4: Отправить токен боту в Telegram

```
/token eyJhbGciOiJIUzI1NiIs...
```

Бот ответит: *«Токен принят и сохранён.»*

### Шаг 5: Задать вопрос LLM

Просто отправьте текстовое сообщение:

```
Что такое микросервисная архитектура?
```

Бот ответит: *«Запрос принят. Ожидайте ответа от LLM...»*

Через несколько секунд придёт ответ от LLM.

### Сценарии отказа

- Без `/token` — бот откажет: *«У вас нет сохранённого токена»*
- С невалидным/просроченным токеном — бот откажет: *«Ваш токен истёк или невалиден»*
- Повторная регистрация с тем же email — `409 User with this email already exists`
- Неверный пароль при логине — `401 Invalid email or password`

## Запуск тестов

Тесты запускаются **локально без Docker** и без внешних сервисов:

```bash
# Auth Service — 11 тестов
cd auth_service
uv sync
uv run pytest app/tests/ -v

# Bot Service — 13 тестов
cd ../bot_service
uv sync
uv run pytest app/tests/ -v
```

### Состав тестов

**Auth Service (11 тестов):**

| Тип | Файл | Что проверяется |
|-----|-------|-----------------|
| Unit | `test_security.py` | Хеш пароля != plain, verify correct/wrong, JWT create/decode, decode invalid |
| Unit | `test_usecase.py` | Гонка на регистрации: `IntegrityError` из БД превращается в корректный `409 UserAlreadyExistsError` |
| Integration | `test_integration.py` | register→login→me, дубликат 409, wrong password 401, /me без токена 401, /me с невалидным токеном 401 |

**Bot Service (13 тестов):**

| Тип | Файл | Что проверяется |
|-----|-------|-----------------|
| Unit | `test_jwt.py` | decode valid/invalid/expired/wrong_secret |
| Mock | `test_handlers.py` | /token сохраняет в Redis, /token отклоняет невалидный, текст без токена → отказ, текст с токеном → `llm_request.delay()` |
| Integration | `test_openrouter.py` | OpenRouter success, OpenRouter error 500, malformed response |
| Integration | `test_llm_tasks.py` | Реальный Celery task path: OpenRouter → Telegram, плюс fallback при сбое OpenRouter |

Все тесты используют моки:
- **fakeredis** — вместо реального Redis
- **pytest-mock** — мок `llm_request.delay()` (без реального RabbitMQ)
- **respx** — мок HTTP-запросов к OpenRouter
- **temporary SQLite** — изолированная БД на каждый интеграционный тест Auth Service

## Мониторинг

| Инструмент | URL | Логин |
|------------|-----|-------|
| Swagger Auth Service | http://localhost:8000/docs | — |
| RabbitMQ Management | http://localhost:15672 | guest / guest |

### Проверка RabbitMQ

В интерфейсе RabbitMQ должны быть видны:
- Очередь `celery` с 1 consumer (Celery worker)
- Активные connections от Celery worker
- Exchanges для маршрутизации задач

### Проверка Redis

```bash
docker exec <redis_container> redis-cli keys '*'
```

После отправки `/token` боту появится ключ `token:<tg_user_id>`.

### Логи сервисов

```bash
docker compose logs auth_service
docker compose logs bot
docker compose logs celery_worker
```

## Демонстрация работы

### Auth Service (Swagger UI)

**Регистрация пользователя** — `POST /auth/register` возвращает JWT-токен:

![Register](screenshots/api_register.png)

**Авторизация в Swagger** — OAuth2 через `/auth/login`:

![Authorize](screenshots/api_authorize.png)

![Authorized](screenshots/api_authorized.png)

**Логин** — `POST /auth/login` возвращает JWT-токен:

![Login](screenshots/api_login.png)

**Профиль пользователя** — `GET /auth/me` по Bearer-токену:

![Me](screenshots/api_auth.png)

### Telegram-бот

Пользовательский сценарий: `/start` → `/token <jwt>` → вопрос → ответ от LLM:

![Telegram Bot Step 1](screenshots/tg_bot_test_1.png)

![Telegram Bot Step 2](screenshots/tg_bot_test_2.png)

![Telegram Bot Step 3](screenshots/tg_bot_test_3.png)

### RabbitMQ Management

Активные очереди, connections и consumers подтверждают работу асинхронной обработки:

![RabbitMQ](screenshots/rabbit.png)

### Тесты

**Auth Service** — 11 тестов (unit + integration):

![Auth Tests](screenshots/auth_tests.png)

**Bot Service** — 13 тестов (unit + mock + integration):

![Bot Tests](screenshots/bot_tests.png)

## Технологический стек

| Компонент | Технология |
|-----------|------------|
| Auth API | FastAPI, uvicorn |
| База данных | SQLite + aiosqlite, SQLAlchemy (async) |
| Хеширование паролей | passlib + bcrypt |
| JWT | python-jose (HS256) |
| Telegram-бот | aiogram 3 |
| Очередь задач | Celery + RabbitMQ |
| Кэш / хранилище | Redis |
| LLM | OpenRouter API (httpx) |
| Контейнеризация | Docker, Docker Compose |
| Пакетный менеджер | uv |
| Тестирование | pytest, pytest-asyncio, fakeredis, respx, pytest-mock |
