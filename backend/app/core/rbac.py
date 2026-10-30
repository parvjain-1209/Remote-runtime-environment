"""
Role-Based Access Control (RBAC) Dependencies.
"""

from typing import Callable
from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.user import User


def require_roles(*roles: str) -> Callable:
    """
    Dependency factory that enforces user role authorization.
    Reads current user from the JWT, loads the role from the DATABASE (via get_current_user).
    Raises 401 if token is missing or invalid, or 403 if the role is not allowed.
    """
    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if roles and current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return current_user

    return role_dependency
