from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.problem import Problem
from app.models.test_case import TestCase
from app.schemas.test_case import TestCaseCreate, TestCaseResponse, TestCaseUpdate


class TestCaseService:
    @staticmethod
    async def create_test_case(
        db: AsyncSession, problem_id: str, data: TestCaseCreate
    ) -> TestCaseResponse:
        problem_res = await db.execute(select(Problem.id).where(Problem.id == problem_id))
        if not problem_res.scalar_one_or_none():
            raise NotFoundException(message=f"Problem '{problem_id}' not found")

        test_case = TestCase(
            problem_id=problem_id,
            input_data=data.input_data,
            expected_output=data.expected_output,
            is_hidden=data.is_hidden,
            score_weight=data.score_weight,
        )

        db.add(test_case)
        await db.flush()
        await db.refresh(test_case)
        return TestCaseResponse.model_validate(test_case)

    @staticmethod
    async def list_by_problem(
        db: AsyncSession, problem_id: str
    ) -> List[TestCaseResponse]:
        problem_res = await db.execute(select(Problem.id).where(Problem.id == problem_id))
        if not problem_res.scalar_one_or_none():
            raise NotFoundException(message=f"Problem '{problem_id}' not found")

        result = await db.execute(
            select(TestCase)
            .where(TestCase.problem_id == problem_id)
            .order_by(TestCase.is_hidden.asc(), TestCase.created_at.asc())
        )
        return [TestCaseResponse.model_validate(tc) for tc in result.scalars().all()]

    @staticmethod
    async def update_test_case(
        db: AsyncSession, test_case_id: str, data: TestCaseUpdate
    ) -> TestCaseResponse:
        result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
        test_case = result.scalar_one_or_none()

        if not test_case:
            raise NotFoundException(message=f"Test case '{test_case_id}' not found")

        if data.input_data is not None:
            test_case.input_data = data.input_data
        if data.expected_output is not None:
            test_case.expected_output = data.expected_output
        if data.is_hidden is not None:
            test_case.is_hidden = data.is_hidden
        if data.score_weight is not None:
            test_case.score_weight = data.score_weight

        await db.flush()
        await db.refresh(test_case)
        return TestCaseResponse.model_validate(test_case)

    @staticmethod
    async def delete_test_case(db: AsyncSession, test_case_id: str) -> None:
        result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
        test_case = result.scalar_one_or_none()

        if not test_case:
            raise NotFoundException(message=f"Test case '{test_case_id}' not found")

        await db.delete(test_case)
        await db.flush()
