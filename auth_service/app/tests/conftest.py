import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.db.base import Base
from app.main import app


@pytest.fixture
async def client(tmp_path):
    db_path = tmp_path / "test_auth.db"
    engine_test = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    test_session_local = async_sessionmaker(
        engine_test,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with test_session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    app.dependency_overrides.pop(get_db, None)
    await engine_test.dispose()
