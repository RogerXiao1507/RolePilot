from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RolePilot API"
    database_url: str
    openai_api_key: str = ""
    jwt_secret: str = "change-me"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()