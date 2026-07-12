from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    database_url: str

    upload_dir: Path = PROJECT_ROOT / "uploads"
    max_upload_size_mb: int = 25

    allowed_file_extensions: set[str] = {
        "pdf",
        "docx",
        "txt",
        "csv",
        "xlsx",
    }

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()