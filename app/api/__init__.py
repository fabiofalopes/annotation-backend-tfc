from fastapi import APIRouter
from . import auth, admin, projects, chat_disentanglement, imported_data

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(chat_disentanglement.router, prefix="/chat", tags=["chat"])
api_router.include_router(imported_data.router, prefix="/data-items/import", tags=["imported-data"])

__all__ = ["auth", "admin", "projects", "chat_disentanglement", "imported_data"] 