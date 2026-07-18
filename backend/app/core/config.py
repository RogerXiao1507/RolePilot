from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RolePilot API"
    database_url: str
    openai_api_key: str = ""
    auth_issuer: str
    auth_audience: str
    auth_jwks_url: str | None = None
    max_resume_upload_bytes: int = 10 * 1024 * 1024
    max_resume_pages: int = 10
    max_resume_text_chars: int = 100_000
    job_url_timeout_seconds: float = 15.0
    job_url_max_redirects: int = 3
    job_url_max_response_bytes: int = 2 * 1024 * 1024

    @field_validator("auth_issuer")
    @classmethod
    def validate_auth_issuer(cls, value: str) -> str:
        issuer = value.strip()
        if not issuer.startswith("https://"):
            raise ValueError("AUTH_ISSUER must be an HTTPS URL")
        return f"{issuer.rstrip('/')}/"

    @field_validator("auth_audience")
    @classmethod
    def validate_auth_audience(cls, value: str) -> str:
        audience = value.strip()
        if not audience:
            raise ValueError("AUTH_AUDIENCE cannot be empty")
        return audience

    @field_validator("auth_jwks_url")
    @classmethod
    def validate_auth_jwks_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        url = value.strip()
        if not url.startswith("https://"):
            raise ValueError("AUTH_JWKS_URL must be an HTTPS URL")
        return url

    @property
    def resolved_auth_jwks_url(self) -> str:
        return self.auth_jwks_url or f"{self.auth_issuer}.well-known/jwks.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
