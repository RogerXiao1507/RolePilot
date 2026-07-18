from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RolePilot API"
    database_url: str
    openai_api_key: str = ""
    jwt_secret: str = "change-me"
    max_resume_upload_bytes: int = 10 * 1024 * 1024
    max_resume_pages: int = 10
    max_resume_text_chars: int = 100_000
    job_url_timeout_seconds: float = 15.0
    job_url_max_redirects: int = 3
    job_url_max_response_bytes: int = 2 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
