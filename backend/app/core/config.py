from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RolePilot API"
    database_url: str
    openai_api_key: str = ""
    auth_issuer: str
    auth_audience: str
    auth_jwks_url: str | None = None
    object_storage_bucket: str | None = None
    object_storage_endpoint_url: str | None = None
    object_storage_region: str = "us-east-1"
    object_storage_access_key_id: str | None = None
    object_storage_secret_access_key: str | None = None
    object_storage_signed_url_seconds: int = 300
    object_storage_sse_algorithm: str | None = "AES256"
    object_storage_required: bool = False
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

    @model_validator(mode="after")
    def validate_object_storage_configuration(self):
        required_values = {
            "OBJECT_STORAGE_BUCKET": self.object_storage_bucket,
            "OBJECT_STORAGE_ACCESS_KEY_ID": self.object_storage_access_key_id,
            "OBJECT_STORAGE_SECRET_ACCESS_KEY": self.object_storage_secret_access_key,
        }
        configured_count = sum(bool(value) for value in required_values.values())
        if configured_count not in {0, len(required_values)}:
            missing = ", ".join(
                name for name, value in required_values.items() if not value
            )
            raise ValueError(f"Private object storage configuration is incomplete: {missing}")
        if self.object_storage_required and configured_count == 0:
            raise ValueError(
                "Private object storage is required but its bucket and credentials are missing"
            )
        return self

    @property
    def resolved_auth_jwks_url(self) -> str:
        return self.auth_jwks_url or f"{self.auth_issuer}.well-known/jwks.json"

    @property
    def object_storage_enabled(self) -> bool:
        return bool(
            self.object_storage_bucket
            and self.object_storage_access_key_id
            and self.object_storage_secret_access_key
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
