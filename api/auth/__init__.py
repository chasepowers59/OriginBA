"""Portal identity and access control (separate from Oracle analytics DB)."""

from api.auth.bootstrap import init_auth_database
from api.auth.dependencies import AuthContext, get_auth_context, require_permission, require_role
from api.auth.routes import router as auth_router

__all__ = [
    "AuthContext",
    "auth_router",
    "get_auth_context",
    "init_auth_database",
    "require_permission",
    "require_role",
]
