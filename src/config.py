from pydantic import AnyUrl, BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseModel):
    token: SecretStr
    admins: list[int] = Field(default_factory=list)


class DatabaseSettings(BaseModel):
    url: AnyUrl
    echo: bool = Field(default=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
    )

    # Telegram
    bot: BotSettings

    # Database
    db: DatabaseSettings


settings = Settings()  # type: ignore
