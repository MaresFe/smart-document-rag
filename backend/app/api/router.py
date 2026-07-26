from fastapi import APIRouter

from app.api.routes import auth, chat, documents, search


api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(search.router)
api_router.include_router(chat.router)