from fastapi import APIRouter

from app.api.routes import documents


api_router = APIRouter(prefix="/api")

api_router.include_router(documents.router)