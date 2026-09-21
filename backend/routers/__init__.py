from .schemes import router as schemes_router
from .applications import router as applications_router
from .admin import router as admin_router

__all__ = ["schemes_router", "applications_router", "admin_router"]
