from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.common import MessageResponse, StandardResponse
from app.schemas.test_case import TestCaseCreate, TestCaseResponse, TestCaseUpdate
from app.services.test_case_service import TestCaseService
from app.utils.api_response import make_response

router = APIRouter()


@router.post(
    "/problems/{problem_id}/test-cases",
    response_model=StandardResponse[TestCaseResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add a test case to a problem (Recruiter/Admin only)",
)
async def create_test_case(
    problem_id: str,
    data: TestCaseCreate,
    _recruiter: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[TestCaseResponse]:
    tc = await TestCaseService.create_test_case(db, problem_id, data)
    return make_response(
        data=tc,
        message="Test case created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/problems/{problem_id}/test-cases",
    response_model=StandardResponse[List[TestCaseResponse]],
    summary="List all test cases for a problem (Recruiter/Admin only)",
)
async def list_test_cases(
    problem_id: str,
    _recruiter: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[List[TestCaseResponse]]:
    tcs = await TestCaseService.list_by_problem(db, problem_id)
    return make_response(data=tcs, message="Test cases retrieved")


@router.put(
    "/test-cases/{test_case_id}",
    response_model=StandardResponse[TestCaseResponse],
    summary="Update an existing test case (Recruiter/Admin only)",
)
async def update_test_case(
    test_case_id: str,
    data: TestCaseUpdate,
    _recruiter: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[TestCaseResponse]:
    updated = await TestCaseService.update_test_case(db, test_case_id, data)
    return make_response(data=updated, message="Test case updated successfully")


@router.delete(
    "/test-cases/{test_case_id}",
    response_model=MessageResponse,
    summary="Delete a test case (Recruiter/Admin only)",
)
async def delete_test_case(
    test_case_id: str,
    _recruiter: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.RECRUITER])),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await TestCaseService.delete_test_case(db, test_case_id)
    return MessageResponse(success=True, message="Test case deleted successfully")
