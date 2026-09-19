from typing import Callable, List, Optional
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import RoleEnum
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not auth or not auth.credentials:
        raise UnauthorizedException(message="Authentication credentials were not provided")

    token = auth.credentials
    payload = decode_token(token)

    if not payload:
        raise UnauthorizedException(message="Invalid or expired authentication token")

    token_type = payload.get("type")
    if token_type != "access":
        raise UnauthorizedException(message="Invalid token type, expected access token")

    user_id: str = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(message="Token does not contain valid user identification")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(message="User associated with this token no longer exists")

    return user


async def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not auth or not auth.credentials:
        return None

    token = auth.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        return None

    user_id: str = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def require_roles(allowed_roles: List[RoleEnum]) -> Callable:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenException(
                message=f"Action forbidden for role '{current_user.role.value}'. Requires one of: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return role_checker
