from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    ADVANCED_CHECKER: bool = True

    REF_LINK: str = "https://t.me/pocketfi_bot/Mining?startapp=6624523270"

    USE_PROXY_FROM_FILE: bool = False


settings = Settings()


