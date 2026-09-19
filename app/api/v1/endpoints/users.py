from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.common import PaginatedResponse, StandardResponse
from app.schemas.user import UserResponse, UserUpdateRoleRequest
from app.services.auth_service import AuthService
from app.utils.api_response import make_paginated_response, make_response
from app.utils.pagination import paginate

router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedResponse[UserResponse],
    summary="List all users with search and pagination (Admin only)",
)
async def list_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[RoleEnum] = Query(None, description="Filter by role"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    _admin: User = Depends(require_roles([RoleEnum.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[UserResponse]:
    query = select(User)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(
            (User.name.ilike(search_term)) | (User.email.ilike(search_term))
        )

    if role:
        query = query.where(User.role == role)

    query = query.order_by(User.created_at.desc())

    result = await paginate(db, query, page=page, page_size=limit)
    users_data = [UserResponse.model_validate(u) for u in result.items]

    return make_paginated_response(
        data=users_data,
        pagination=result.meta,
        message="Users retrieved successfully",
    )


@router.get(
    "/{user_id}",
    response_model=StandardResponse[UserResponse],
    summary="Get user profile details by ID (Admin only)",
)
async def get_user(
    user_id: str,
    _admin: User = Depends(require_roles([RoleEnum.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[UserResponse]:
    user = await AuthService.get_user_by_id(db, user_id)
    return make_response(data=user, message="User retrieved successfully")


@router.patch(
    "/{user_id}/role",
    response_model=StandardResponse[UserResponse],
    summary="Update a user's role (Admin only)",
)
async def update_user_role(
    user_id: str,
    data: UserUpdateRoleRequest,
    _admin: User = Depends(require_roles([RoleEnum.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[UserResponse]:
    updated_user = await AuthService.update_user_role(db, user_id, data)
    return make_response(
        data=updated_user,
        message=f"User role updated to '{data.role.value}' successfully",
    )


@router.delete(
    "/{user_id}",
    response_model=StandardResponse[dict],
    summary="Delete a user account (Admin only)",
)
async def delete_user(
    user_id: str,
    _admin: User = Depends(require_roles([RoleEnum.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    await AuthService.delete_user(db, user_id)
    return make_response(data={"user_id": user_id}, message="User deleted successfully")
