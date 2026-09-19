from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.enums import SubmissionStatusEnum
from app.models.user import User
from app.schemas.common import PaginatedResponse, SortOrderEnum, StandardResponse
from app.schemas.submission import (
    RunSampleCodeRequest,
    SampleExecutionResult,
    SubmissionCreate,
    SubmissionDetailResponse,
    SubmissionResponse,
)
from app.services.submission_service import SubmissionService
from app.utils.api_response import make_paginated_response, make_response

router = APIRouter()


@router.post(
    "/run-sample",
    response_model=StandardResponse[SampleExecutionResult],
    summary="Dry run code against problem sample input or custom stdin (No submission saved)",
)
async def run_sample_code(
    data: RunSampleCodeRequest,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[SampleExecutionResult]:
    result = await SubmissionService.run_sample(db, data)
    return make_response(
        data=result,
        message=f"Dry run executed with status: {result.status.value}",
    )


@router.post(
    "/",
    response_model=StandardResponse[SubmissionDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit source code for isolated execution and grading",
)
async def submit_code(
    data: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[SubmissionDetailResponse]:
    result = await SubmissionService.create_and_evaluate(db, current_user, data)
    return make_response(
        data=result,
        message=f"Submission evaluated with status: {result.status.value}",
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/",
    response_model=PaginatedResponse[SubmissionResponse],
    summary="List submissions with filters, sorting, and pagination",
)
async def list_submissions(
    problem_id: Optional[str] = Query(None, description="Filter by problem ID"),
    assessment_id: Optional[str] = Query(None, description="Filter by assessment ID"),
    status: Optional[SubmissionStatusEnum] = Query(None, description="Filter by submission status"),
    candidate_id: Optional[str] = Query(None, description="Filter by candidate ID (Recruiter/Admin only)"),
    sort_order: SortOrderEnum = Query(SortOrderEnum.DESC, description="Sort direction by date"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SubmissionResponse]:
    result = await SubmissionService.list_submissions(
        db=db,
        user=current_user,
        problem_id=problem_id,
        assessment_id=assessment_id,
        status=status,
        candidate_id=candidate_id,
        sort_order=sort_order,
        page=page,
        page_size=limit,
    )
    return make_paginated_response(
        data=result.items,
        pagination=result.meta,
        message="Submissions retrieved successfully",
    )


@router.get(
    "/{submission_id}",
    response_model=StandardResponse[SubmissionDetailResponse],
    summary="Get detailed submission execution result",
)
async def get_submission(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[SubmissionDetailResponse]:
    result = await SubmissionService.get_submission_detail(db, submission_id, current_user)
    return make_response(data=result, message="Submission details retrieved")
