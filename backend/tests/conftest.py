import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# Testler gerçek proje sırlarına veya çalışan veritabanına bağlı olmamalıdır.
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("POSTGRES_DB", "test_database")
os.environ.setdefault(
    "DATABASE_URL",
    (
        "postgresql+psycopg://test_user:"
        "test_password@localhost:5432/test_database"
    ),
)
os.environ.setdefault(
    "AUTH_SECRET_KEY",
    "test-only-secret-key-that-is-not-used-in-production",
)
