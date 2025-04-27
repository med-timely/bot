from pydantic import AnyUrl, BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseModel):
    token: SecretStr
    admins: list[int] = Field(default_factory=list)


class DatabaseSettings(BaseModel):
    url: AnyUrl
    echo: bool = Field(default=False)


class LLMSettings(BaseModel):
    url: AnyUrl | None = None
    default_model: str | None = None
    timeout: int = 30
    api_key: SecretStr


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

    # LLM
    llm: LLMSettings


settings = Settings()  # type: ignore
