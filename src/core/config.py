from functools import lru_cache
from typing import Annotated

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, SecretStr, RedisDsn

Port = Annotated[int, Field(ge=0, le=65535)]
NonEmptyStr = Annotated[str, Field(min_length=2)]


class Settings(BaseSettings):
    PROJECT_NAME: NonEmptyStr
    DEBUG: bool
    ALLOWED_ORIGINS: list[str] = ["*"]
    LOG_LEVEL: NonEmptyStr

    postgres_user: NonEmptyStr
    postgres_password: SecretStr
    postgres_host: NonEmptyStr
    postgres_port: Port
    postgres_db: NonEmptyStr

    # postgres_user_test: NonEmptyStr
    # postgres_password_test: SecretStr
    # postgres_host_test: NonEmptyStr
    # postgres_port_test: Port
    # postgres_db_test: NonEmptyStr

    # redis_host: NonEmptyStr
    # redis_port: Port

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

    # @property
    # def database_url_test(self) -> str:
    #     return str(
    #         PostgresDsn.build(
    #             scheme="postgresql+asyncpg",
    #             username=self.postgres_user_test,
    #             password=self.postgres_password_test.get_secret_value(),
    #             host=self.postgres_host_test,
    #             port=self.postgres_port_test,
    #             path=self.postgres_db_test,
    #         )
    #     )

    # @property
    # def redis_url(self) -> str:
    #     return str(
    #         RedisDsn.build(
    #             scheme="redis",
    #             host=self.redis_host,
    #             port=self.redis_port,
    #             path="0",
    #         )
    #     )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
