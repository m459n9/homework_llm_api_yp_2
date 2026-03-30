import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import UserAlreadyExistsError
from app.usecases.auth import AuthUseCase


class DuplicateOnCreateRepo:
    async def get_by_email(self, email: str):
        return None

    async def create(self, email: str, password_hash: str, role: str = "user"):
        raise IntegrityError(
            statement="INSERT INTO users ...",
            params={"email": email},
            orig=Exception("UNIQUE constraint failed: users.email"),
        )


@pytest.mark.asyncio
async def test_register_maps_integrity_error_to_user_already_exists():
    uc = AuthUseCase(DuplicateOnCreateRepo())

    with pytest.raises(UserAlreadyExistsError):
        await uc.register("surname@email.com", "strongpass123")
