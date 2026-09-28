from .schemes import router as schemes_router
from .applications import router as applications_router
from .admin import router as admin_router
from .auth import router as auth_router
from .private_documents import router as private_documents_router

__all__ = [
    "schemes_router", "applications_router", "admin_router",
    "auth_router", "private_documents_router"
]
