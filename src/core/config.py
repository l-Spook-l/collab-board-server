from functools import lru_cache
from typing import Annotated

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Port = Annotated[int, Field(ge=0, le=65535)]
NonEmptyStr = Annotated[str, Field(min_length=2)]


class Settings(BaseSettings):
    PROJECT_NAME: NonEmptyStr
    DEBUG: bool
    ALLOWED_ORIGINS: list[str] = ["*"]
    LOG_LEVEL: NonEmptyStr
    FRONTEND_URL: NonEmptyStr

    STRIPE_SECRET_KEY: SecretStr
    STRIPE_PRICE_ID: NonEmptyStr
    STRIPE_WEBHOOK_SECRET: SecretStr

    postgres_user: NonEmptyStr
    postgres_password: SecretStr
    postgres_host: NonEmptyStr
    postgres_port: Port
    postgres_db: NonEmptyStr

    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    AUTH0_DOMAIN: str
    AUTH0_AUDIENCE: str
    AUTH0_NAMESPACE: str

    @property
    def database_url(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password.get_secret_value(),
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
