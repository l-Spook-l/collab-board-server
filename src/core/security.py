import logging
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from src.core.config import settings
from src.core.exceptions.custom_exceptions import (
    InvalidAuth0TokenError,
    InvalidTokenError,
)

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError as e:
        logger.warning("Token invalid", extra={"detail": str(e)})
        raise InvalidTokenError()


def decode_auth0_token(token: str, jwks: dict) -> dict:
    try:
        # Получаем заголовок JWT.
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        # Ищем нужный публичный ключ Auth0.
        public_key = next(
            (
                key
                for key in jwks["keys"]
                if key.get("kid") == kid
                and key.get("kty") == "RSA"
                and key.get("use", "sig") == "sig"
            ),
            None,
        )

        # Если подходящий ключ не найден — отклоняем токен.
        if public_key is None:
            raise JWTError("Public key not found")

        # Проверяем подпись и основные JWT claims.
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.AUTH0_AUDIENCE,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )

        return payload

    except (JWTError, KeyError, ValueError) as e:
        # Логируем причину, но не сам токен.
        logger.warning("Auth0 JWT validation failed: %s", e)

        raise InvalidAuth0TokenError() from e
