from datetime import datetime
from typing import Optional, Union
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_optional, get_db, require_roles
from app.models.enums import DifficultyEnum, RoleEnum
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse, SortOrderEnum, StandardResponse
from app.schemas.problem import (
    ProblemAdminDetailResponse,
    ProblemCreate,
    ProblemDetailResponse,
    ProblemResponse,
    ProblemUpdate,
)
from app.services.problem_service import ProblemService
from app.utils.api_response import make_paginated_response, make_response

router = APIRouter()


@router.post(
    "/",
    response_model=StandardResponse[ProblemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new coding challenge/problem (Recruiter/Admin only)",
)
async def create_problem(
    data: ProblemCreate,
    _recruiter: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[ProblemResponse]:
    problem = await ProblemService.create_problem(db, data)
    return make_response(
        data=problem,
        message="Problem created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/",
    response_model=PaginatedResponse[ProblemResponse],
    summary="List coding problems with search, filtering, sorting, and pagination",
)
async def list_problems(
    search: Optional[str] = Query(None, description="Search by title, slug, or category"),
    difficulty: Optional[DifficultyEnum] = Query(None, description="Filter by difficulty"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_published: Optional[bool] = Query(None, description="Filter by publication status (Admin/Recruiter only)"),
    created_after: Optional[datetime] = Query(None, description="Filter problems created after date"),
    created_before: Optional[datetime] = Query(None, description="Filter problems created before date"),
    sort_by: str = Query("created_at", description="Sort field: created_at, title, difficulty, category, time_limit_ms"),
    sort_order: SortOrderEnum = Query(SortOrderEnum.DESC, description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProblemResponse]:
    result = await ProblemService.list_problems(
        db=db,
        search=search,
        difficulty=difficulty,
        category=category,
        is_published=is_published,
        created_after=created_after,
        created_before=created_before,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=limit,
        user=current_user,
    )
    return make_paginated_response(
        data=result.items,
        pagination=result.meta,
        message="Problems retrieved successfully",
    )


@router.get(
    "/{id_or_slug}",
    response_model=StandardResponse[Union[ProblemAdminDetailResponse, ProblemDetailResponse]],
    summary="Get problem details and visible sample test cases",
)
async def get_problem(
    id_or_slug: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[Union[ProblemAdminDetailResponse, ProblemDetailResponse]]:
    problem = await ProblemService.get_problem_detail(db, id_or_slug, user=current_user)
    return make_response(data=problem, message="Problem details retrieved")


@router.put(
    "/{problem_id}",
    response_model=StandardResponse[ProblemResponse],
    summary="Update problem details (Recruiter/Admin only)",
)
async def update_problem(
    problem_id: str,
    data: ProblemUpdate,
    _recruiter: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[ProblemResponse]:
    updated = await ProblemService.update_problem(db, problem_id, data)
    return make_response(data=updated, message="Problem updated successfully")


@router.delete(
    "/{problem_id}",
    response_model=MessageResponse,
    summary="Delete a problem and associated test cases (Recruiter/Admin only)",
)
async def delete_problem(
    problem_id: str,
    _recruiter: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await ProblemService.delete_problem(db, problem_id)
    return MessageResponse(success=True, message="Problem deleted successfully")
