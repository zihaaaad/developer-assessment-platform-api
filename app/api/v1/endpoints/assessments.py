from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_optional, get_db, require_roles
from app.models.enums import AssessmentStatusEnum, RoleEnum
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentDetailResponse,
    AssessmentProblemAdd,
    AssessmentResponse,
    AssessmentUpdate,
)
from app.schemas.common import MessageResponse, PaginatedResponse, SortOrderEnum, StandardResponse
from app.services.assessment_service import AssessmentService
from app.utils.api_response import make_paginated_response, make_response

router = APIRouter()


@router.post(
    "/",
    response_model=StandardResponse[AssessmentDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new assessment/contest (Recruiter/Admin only)",
)
async def create_assessment(
    data: AssessmentCreate,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[AssessmentDetailResponse]:
    assessment = await AssessmentService.create_assessment(db, current_user, data)
    return make_response(
        data=assessment,
        message="Assessment created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/",
    response_model=PaginatedResponse[AssessmentResponse],
    summary="List assessments with search, status filtering, and pagination",
)
async def list_assessments(
    search: Optional[str] = Query(None, description="Search by title or description"),
    status: Optional[AssessmentStatusEnum] = Query(None, description="Filter by status (DRAFT, PUBLISHED, ARCHIVED)"),
    sort_by: str = Query("start_time", description="Sort field: start_time, end_time, created_at, title"),
    sort_order: SortOrderEnum = Query(SortOrderEnum.DESC, description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AssessmentResponse]:
    result = await AssessmentService.list_assessments(
        db=db,
        search=search,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=limit,
        user=current_user,
    )
    return make_paginated_response(
        data=result.items,
        pagination=result.meta,
        message="Assessments retrieved successfully",
    )


@router.get(
    "/{assessment_id}",
    response_model=StandardResponse[AssessmentDetailResponse],
    summary="Get assessment details and assigned problems",
)
async def get_assessment(
    assessment_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[AssessmentDetailResponse]:
    assessment = await AssessmentService.get_assessment_detail(db, assessment_id, user=current_user)
    return make_response(data=assessment, message="Assessment details retrieved")


@router.put(
    "/{assessment_id}",
    response_model=StandardResponse[AssessmentResponse],
    summary="Update assessment metadata and schedule (Recruiter/Admin only)",
)
async def update_assessment(
    assessment_id: str,
    data: AssessmentUpdate,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[AssessmentResponse]:
    updated = await AssessmentService.update_assessment(db, assessment_id, data, current_user)
    return make_response(data=updated, message="Assessment updated successfully")


@router.post(
    "/{assessment_id}/problems",
    response_model=MessageResponse,
    summary="Add or update a problem link in an assessment (Recruiter/Admin only)",
)
async def add_problem_to_assessment(
    assessment_id: str,
    data: AssessmentProblemAdd,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await AssessmentService.add_problem(db, assessment_id, data, current_user)
    return MessageResponse(success=True, message="Problem added to assessment successfully")


@router.delete(
    "/{assessment_id}/problems/{problem_id}",
    response_model=MessageResponse,
    summary="Remove a problem from an assessment (Recruiter/Admin only)",
)
async def remove_problem_from_assessment(
    assessment_id: str,
    problem_id: str,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await AssessmentService.remove_problem(db, assessment_id, problem_id, current_user)
    return MessageResponse(success=True, message="Problem removed from assessment successfully")


@router.get(
    "/{assessment_id}/plagiarism-report",
    response_model=StandardResponse[dict],
    summary="Generate AST and token similarity plagiarism report for candidate submissions (Recruiter/Admin only)",
)
async def get_plagiarism_report(
    assessment_id: str,
    threshold: float = Query(0.70, ge=0.1, le=1.0, description="Similarity threshold (0.0 to 1.0)"),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    from app.services.plagiarism_service import PlagiarismService

    report = await PlagiarismService.analyze_assessment(
        db=db,
        assessment_id=assessment_id,
        similarity_threshold=threshold,
    )
    return make_response(data=report, message="Plagiarism analysis completed successfully")


@router.delete(
    "/{assessment_id}",
    response_model=MessageResponse,
    summary="Delete an assessment (Recruiter/Admin only)",
)
async def delete_assessment(
    assessment_id: str,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await AssessmentService.delete_assessment(db, assessment_id, current_user)
    return MessageResponse(success=True, message="Assessment deleted successfully")
