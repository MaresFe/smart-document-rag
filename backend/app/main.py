from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.db.session import check_database_connection


app = FastAPI(
    title="Smart Document RAG API",
    description="Backend API for document-based question answering system.",
    version="0.1.0",
)


app.include_router(api_router)


@app.get("/")
def read_root():
    return {
        "message": "Smart Document RAG API is running."
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


@app.get("/health/db")
def database_health_check():
    try:
        check_database_connection()
        return {
            "database": "connected"
        }
    except SQLAlchemyError as error:
        return {
            "database": "error",
            "detail": str(error),
        }