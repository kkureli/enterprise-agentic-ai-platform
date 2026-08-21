from fastapi import APIRouter

from app.api.v1.documents import router as documents_router
from app.api.v1.rag import router as rag_router
from app.api.v1.retrieval import router as retrieval_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.users import router as users_router

api_router = APIRouter()

api_router.include_router(tenants_router)
api_router.include_router(users_router)
api_router.include_router(documents_router)
api_router.include_router(retrieval_router)
api_router.include_router(rag_router)
