from pathlib import Path
from typing import Literal

from pydantic import SecretStr
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

    auth_secret_key: SecretStr
    auth_algorithm: str = "HS256"
    auth_access_token_minutes: int = 60
    auth_cookie_name: str = (
        "smart_rag_access_token"
    )
    auth_cookie_secure: bool = False

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

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
