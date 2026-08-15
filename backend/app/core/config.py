from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import (
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    database_url: str

    app_environment: Literal[
        "development",
        "test",
        "production",
    ] = "development"
    cors_allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    trusted_hosts: list[str] = [
        "localhost",
        "127.0.0.1",
        "testserver",
    ]
    security_hsts_enabled: bool = False
    security_hsts_max_age_seconds: int = Field(
        default=31_536_000,
        ge=1,
    )
    security_hsts_include_subdomains: bool = True

    upload_dir: Path = PROJECT_ROOT / "uploads"
    max_upload_size_mb: int = 25

    ocr_enabled: bool = True
    ocr_languages: str = "tur+eng"
    ocr_dpi: int = 180
    ocr_max_pages: int = 25
    ocr_page_timeout_seconds: int = 20
    ocr_min_text_characters: int = 10
    ocr_max_pixels_per_page: int = 20_000_000

    embedding_model_name: str = (
        "intfloat/multilingual-e5-large"
    )
    embedding_dimension: int = 1024

    retrieval_min_query_characters: int = 2
    retrieval_min_similarity_score: float = 0.75

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9b"
    ollama_keep_alive: str = "30m"
    llm_timeout_seconds: int = 120
    llm_context_window: int = Field(default=8192, ge=2048, le=32768)
    llm_max_output_tokens: int = Field(default=384, ge=64, le=4096)
    llm_structured_max_output_tokens: int = Field(
        default=1024,
        ge=128,
        le=4096,
    )

    auth_secret_key: SecretStr
    auth_algorithm: str = "HS256"
    auth_access_token_minutes: int = Field(
        default=60,
        ge=1,
    )
    auth_cookie_name: str = (
        "smart_rag_access_token"
    )
    auth_cookie_secure: bool = False
    auth_rate_limit_enabled: bool = True
    auth_rate_limit_max_keys: int = Field(
        default=10_000,
        ge=100,
    )
    auth_login_max_attempts: int = Field(
        default=5,
        ge=1,
    )
    auth_login_window_seconds: int = Field(
        default=60,
        ge=1,
    )
    auth_password_reset_max_attempts: int = Field(
        default=3,
        ge=1,
    )
    auth_password_reset_window_seconds: int = Field(
        default=900,
        ge=1,
    )
    auth_token_max_attempts: int = Field(
        default=10,
        ge=1,
    )
    auth_token_window_seconds: int = Field(
        default=300,
        ge=1,
    )

    registration_mode: Literal[
        "open",
        "invite_only",
    ] = "invite_only"
    account_invitation_hours: int = 24
    account_password_reset_minutes: int = 30

    frontend_base_url: str = "http://localhost:5173"
    email_delivery_mode: Literal[
        "console",
        "smtp",
    ] = "console"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = True
    smtp_from_email: str = "noreply@example.com"
    smtp_timeout_seconds: int = 15

    allowed_file_extensions: set[str] = {
        "pdf",
        "docx",
        "txt",
        "csv",
        "xlsx",
        "png",
        "jpg",
        "jpeg",
    }

    @field_validator("auth_secret_key")
    @classmethod
    def validate_auth_secret_key(
        cls,
        value: SecretStr,
    ) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError(
                "AUTH_SECRET_KEY must contain at least 32 characters."
            )

        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_origins(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized_origins: list[str] = []

        for value in values:
            origin = value.strip().rstrip("/")

            if origin == "*":
                raise ValueError(
                    "Wildcard CORS origins cannot be used with cookies."
                )

            parsed = urlparse(origin)

            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.params
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    f"Invalid CORS origin: {value}"
                )

            normalized_origins.append(origin)

        if not normalized_origins:
            raise ValueError(
                "At least one CORS origin must be configured."
            )

        return list(dict.fromkeys(normalized_origins))

    @field_validator("trusted_hosts")
    @classmethod
    def validate_trusted_hosts(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized_hosts = [
            value.strip()
            for value in values
            if value.strip()
        ]

        if not normalized_hosts:
            raise ValueError(
                "At least one trusted host must be configured."
            )

        if any(
            "://" in host or "/" in host
            for host in normalized_hosts
        ):
            raise ValueError(
                "TRUSTED_HOSTS entries must be host names, not URLs."
            )

        return list(dict.fromkeys(normalized_hosts))

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_environment != "production":
            return self

        if not self.auth_cookie_secure:
            raise ValueError(
                "AUTH_COOKIE_SECURE must be true in production."
            )

        if not self.security_hsts_enabled:
            raise ValueError(
                "SECURITY_HSTS_ENABLED must be true in production."
            )

        if self.email_delivery_mode == "console":
            raise ValueError(
                "EMAIL_DELIVERY_MODE cannot be console in production."
            )

        if "*" in self.trusted_hosts:
            raise ValueError(
                "Wildcard trusted hosts are not allowed in production."
            )

        return self

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
