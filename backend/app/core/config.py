from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    embedding_model_name: str = "intfloat/multilingual-e5-large"
    embedding_dimension: int = 1024

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    llm_timeout_seconds: int = 120

    auth_secret_key: SecretStr
    auth_algorithm: str = "HS256"
    auth_access_token_minutes: int = 60
    auth_cookie_name: str = "smart_rag_access_token"
    auth_cookie_secure: bool = False

    allowed_file_extensions: set[str] = {
        "pdf",
        "docx",
        "txt",
        "csv",
        "xlsx",
    }

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()