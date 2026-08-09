import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import (
    TrustedHostMiddleware,
)

from app.api.router import api_router
from app.core.config import settings
from app.db.session import (
    check_database_connection,
)
from app.middleware.security import (
    ApplicationSecurityMiddleware,
)
from app.services.embedding import (
    EmbeddingError,
    create_query_embedding,
)
from app.services.llm import (
    LLMError,
    warm_up_ollama,
)


startup_logger = logging.getLogger(
    "uvicorn.error",
)


@asynccontextmanager
async def lifespan(
    _app: FastAPI,
) -> AsyncIterator[None]:
    total_started = perf_counter()

    embedding_ready = False
    ollama_ready = False

    embedding_started = perf_counter()

    try:
        create_query_embedding(
            "model warmup",
        )
        embedding_ready = True

    except EmbeddingError as error:
        startup_logger.warning(
            "Embedding warmup failed | "
            "error_type=%s",
            type(error).__name__,
        )

    embedding_ms = (
        perf_counter() - embedding_started
    ) * 1000

    ollama_started = perf_counter()

    try:
        warm_up_ollama()
        ollama_ready = True

    except LLMError as error:
        startup_logger.warning(
            "Ollama startup warmup failed | "
            "error_type=%s",
            type(error).__name__,
        )

    ollama_ms = (
        perf_counter() - ollama_started
    ) * 1000

    total_ms = (
        perf_counter() - total_started
    ) * 1000

    startup_logger.info(
        "Model warmup summary | "
        "embedding_ready=%s | "
        "ollama_ready=%s | "
        "embedding_ms=%.2f | "
        "ollama_ms=%.2f | "
        "total_ms=%.2f",
        embedding_ready,
        ollama_ready,
        embedding_ms,
        ollama_ms,
        total_ms,
    )

    yield


app = FastAPI(
    title="Smart Document RAG API",
    description=(
        "Backend API for document-based "
        "question answering system."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts,
)

app.add_middleware(
    ApplicationSecurityMiddleware,
    allowed_origins=settings.cors_allowed_origins,
    auth_cookie_name=settings.auth_cookie_name,
    hsts_enabled=settings.security_hsts_enabled,
    hsts_max_age_seconds=(
        settings.security_hsts_max_age_seconds
    ),
    hsts_include_subdomains=(
        settings.security_hsts_include_subdomains
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Accept",
        "Content-Type",
    ],
)

app.include_router(api_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": (
            "Smart Document RAG API is running."
        ),
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.get("/health/db")
def database_health_check() -> JSONResponse:
    try:
        check_database_connection()

        return JSONResponse(
            status_code=200,
            content={
                "database": "connected",
            },
        )

    except SQLAlchemyError as error:
        startup_logger.warning(
            "Database health check failed | "
            "error_type=%s",
            type(error).__name__,
        )

        return JSONResponse(
            status_code=503,
            content={
                "database": "error",
            },
        )
