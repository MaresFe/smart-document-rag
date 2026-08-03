import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.db.session import (
    check_database_connection,
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
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def read_root():
    return {
        "message": (
            "Smart Document RAG API is running."
        ),
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }


@app.get("/health/db")
def database_health_check():
    try:
        check_database_connection()

        return {
            "database": "connected",
        }

    except SQLAlchemyError as error:
        return {
            "database": "error",
            "detail": str(error),
        }