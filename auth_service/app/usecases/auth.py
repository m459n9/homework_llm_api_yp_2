from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.repositories.users import UsersRepository
from app.schemas.auth import TokenResponse


class AuthUseCase:
    def __init__(self, repo: UsersRepository) -> None:
        self._repo = repo

    async def register(self, email: str, password: str) -> TokenResponse:
        existing = await self._repo.get_by_email(email)
        if existing:
            raise UserAlreadyExistsError()

        hashed = hash_password(password)
        try:
            user = await self._repo.create(email=email, password_hash=hashed)
        except IntegrityError as exc:
            raise UserAlreadyExistsError() from exc
        token = create_access_token(sub=str(user.id), role=user.role)
        return TokenResponse(access_token=token)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        token = create_access_token(sub=str(user.id), role=user.role)
        return TokenResponse(access_token=token)

    async def me(self, user_id: int) -> User:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        return user
