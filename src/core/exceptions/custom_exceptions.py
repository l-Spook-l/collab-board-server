from fastapi import status


class AppError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str | None = None):
        self.detail = detail or "Bad request"

    def __str__(self):
        return self.detail


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN


class TooManyRequestsError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


class UserNotFoundError(NotFoundError):
    def __init__(self, detail: str = "User not found"):
        super().__init__(detail)


class UserAlreadyExistsError(ConflictError):
    def __init__(self, detail: str = "User with this email already exists"):
        super().__init__(detail)


class UserCreateError(ConflictError):
    def __init__(self, detail: str = "Error occurred while creating user"):
        super().__init__(detail)


class UserUpdateError(ConflictError):
    def __init__(self, detail: str = "Error occurred while updating user"):
        super().__init__(detail)


class UserDeleteError(ConflictError):
    def __init__(self, detail: str = "Error occurred while deleting user"):
        super().__init__(detail)


class NoFieldsToUpdateError(BadRequestError):
    def __init__(self, detail: str = "No fields to update"):
        super().__init__(detail)


class InvalidCredentialsError(UnauthorizedError):
    def __init__(self, detail: str = "Invalid email or password"):
        super().__init__(detail)


class InvalidTokenError(UnauthorizedError):
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail)


class InvalidAuth0TokenError(UnauthorizedError):
    def __init__(self, detail: str = "Invalid Auth0 token"):
        super().__init__(detail)


class MissingEmailInTokenError(UnauthorizedError):
    def __init__(self, detail: str = "Email not found in token"):
        super().__init__(detail)


class PermissionDeniedError(ForbiddenError):
    def __init__(
        self, detail: str = "You don't have permission to perform this action"
    ):
        super().__init__(detail)


class CooldownError(TooManyRequestsError):
    def __init__(
        self,
        seconds_left: int,
        detail: str = "Too many requests. Please try again later",
    ):
        self.seconds_left = seconds_left

        super().__init__(detail)


class InvitationCreateError(ConflictError):
    def __init__(self, detail: str = "Error occurred while creating invitation"):
        super().__init__(detail)


class InvitationNotFoundError(NotFoundError):
    def __init__(self, detail: str = "Invitation not found"):
        super().__init__(detail)
