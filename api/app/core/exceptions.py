class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str | None = None) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class BadRequestError(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(f"{resource} '{identifier}' not found", status_code=404)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden", code: str | None = None) -> None:
        super().__init__(message, status_code=403, code=code)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, status_code=401)


class ConflictError(AppException):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=409)
