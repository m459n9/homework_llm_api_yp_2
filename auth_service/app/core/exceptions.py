from fastapi import HTTPException


class BaseHTTPException(HTTPException):
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


class UserAlreadyExistsError(BaseHTTPException):
    status_code = 409
    detail = "User with this email already exists"


class InvalidCredentialsError(BaseHTTPException):
    status_code = 401
    detail = "Invalid email or password"


class InvalidTokenError(BaseHTTPException):
    status_code = 401
    detail = "Invalid token"


class TokenExpiredError(BaseHTTPException):
    status_code = 401
    detail = "Token has expired"


class UserNotFoundError(BaseHTTPException):
    status_code = 404
    detail = "User not found"


class PermissionDeniedError(BaseHTTPException):
    status_code = 403
    detail = "Permission denied"
