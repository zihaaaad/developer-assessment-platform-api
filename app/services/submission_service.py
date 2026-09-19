from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.enums import AssessmentStatusEnum, RoleEnum, SubmissionStatusEnum
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.test_case import TestCase
from app.models.user import User
from app.sandbox.executor import CodeExecutor
from app.schemas.common import SortOrderEnum
from app.schemas.submission import (
    RunSampleCodeRequest,
    SampleExecutionResult,
    SubmissionCreate,
    SubmissionDetailResponse,
    SubmissionResponse,
    TestCaseRunResult,
)
from app.utils.pagination import PaginatedResult, paginate


class SubmissionService:
    @staticmethod
    async def create_and_evaluate(
        db: AsyncSession, candidate: User, data: SubmissionCreate
    ) -> SubmissionDetailResponse:
        prob_res = await db.execute(
            select(Problem)
            .where(Problem.id == data.problem_id)
            .options(selectinload(Problem.test_cases))
        )
        problem = prob_res.scalar_one_or_none()
        if not problem:
            raise NotFoundException(message=f"Problem '{data.problem_id}' not found")

        assessment: Optional[Assessment] = None
        if data.assessment_id:
            assess_res = await db.execute(
                select(Assessment).where(Assessment.id == data.assessment_id)
            )
            assessment = assess_res.scalar_one_or_none()
            if not assessment:
                raise NotFoundException(message=f"Assessment '{data.assessment_id}' not found")

            if assessment.status != AssessmentStatusEnum.PUBLISHED:
                raise BadRequestException(message="Assessment is not currently active")

            now = datetime.now(timezone.utc)
            start_time = assessment.start_time.replace(tzinfo=timezone.utc) if assessment.start_time.tzinfo is None else assessment.start_time
            end_time = assessment.end_time.replace(tzinfo=timezone.utc) if assessment.end_time.tzinfo is None else assessment.end_time

            if now < start_time:
                raise BadRequestException(message="Assessment has not started yet")
            if now > end_time:
                raise BadRequestException(message="Assessment submission window has closed")

        test_cases: List[TestCase] = problem.test_cases
        total_possible = sum(tc.score_weight for tc in test_cases) or 100

        submission = Submission(
            candidate_id=candidate.id,
            problem_id=problem.id,
            assessment_id=data.assessment_id,
            language=data.language.value,
            code=data.code,
            status=SubmissionStatusEnum.RUNNING,
            score=0,
            max_score=total_possible,
        )
        db.add(submission)
        await db.flush()

        if not test_cases:
            exec_res = await CodeExecutor.run(
                language=data.language,
                source_code=data.code,
                stdin_input=problem.sample_input,
                time_limit_ms=problem.time_limit_ms,
                memory_limit_mb=problem.memory_limit_mb,
            )
            submission.status = exec_res.status
            submission.execution_time_ms = exec_res.execution_time_ms
            submission.error_message = exec_res.error_message
            submission.score = total_possible if exec_res.status == SubmissionStatusEnum.ACCEPTED else 0
            await db.flush()
            return await SubmissionService.get_submission_detail(db, submission.id, candidate)

        all_passed = True
        overall_status = SubmissionStatusEnum.ACCEPTED
        earned_score = 0
        peak_time_ms = 0
        root_error: Optional[str] = None
        test_outcomes: List[Dict[str, Any]] = []

        for tc in test_cases:
            exec_res = await CodeExecutor.run(
                language=data.language,
                source_code=data.code,
                stdin_input=tc.input_data,
                time_limit_ms=problem.time_limit_ms,
                memory_limit_mb=problem.memory_limit_mb,
            )

            peak_time_ms = max(peak_time_ms, exec_res.execution_time_ms)
            actual_norm = CodeExecutor.normalize_output(exec_res.stdout)
            expected_norm = CodeExecutor.normalize_output(tc.expected_output)

            tc_passed = False
            if exec_res.status == SubmissionStatusEnum.ACCEPTED:
                if actual_norm == expected_norm:
                    tc_passed = True
                    earned_score += tc.score_weight
                else:
                    all_passed = False
                    if overall_status == SubmissionStatusEnum.ACCEPTED:
                        overall_status = SubmissionStatusEnum.WRONG_ANSWER
            else:
                all_passed = False
                if overall_status in [SubmissionStatusEnum.ACCEPTED, SubmissionStatusEnum.WRONG_ANSWER]:
                    overall_status = exec_res.status
                if not root_error:
                    root_error = exec_res.error_message or exec_res.stderr

            test_outcomes.append(
                {
                    "test_case_id": tc.id,
                    "is_hidden": tc.is_hidden,
                    "passed": tc_passed,
                    "execution_time_ms": exec_res.execution_time_ms,
                    "score_awarded": tc.score_weight if tc_passed else 0,
                    "max_score": tc.score_weight,
                    "error_message": exec_res.error_message if not tc.is_hidden else None,
                    "stdout": actual_norm if not tc.is_hidden else None,
                    "expected_output": expected_norm if not tc.is_hidden else None,
                }
            )

        submission.status = overall_status if not all_passed else SubmissionStatusEnum.ACCEPTED
        submission.score = earned_score
        submission.execution_time_ms = peak_time_ms
        submission.error_message = root_error
        submission.test_case_results = test_outcomes
        await db.flush()

        if assessment:
            await SubmissionService._update_assessment_result(
                db=db,
                assessment_id=assessment.id,
                candidate_id=candidate.id,
            )

        await db.refresh(submission)
        return await SubmissionService.get_submission_detail(db, submission.id, candidate)

    @staticmethod
    async def _update_assessment_result(
        db: AsyncSession, assessment_id: str, candidate_id: str
    ) -> None:
        sub_query = (
            select(
                Submission.problem_id,
                func.max(Submission.score).label("max_score"),
            )
            .where(
                Submission.assessment_id == assessment_id,
                Submission.candidate_id == candidate_id,
            )
            .group_by(Submission.problem_id)
        )
        sub_res = await db.execute(sub_query)
        rows = sub_res.all()

        total_score = sum(r.max_score for r in rows) if rows else 0
        problems_solved = sum(1 for r in rows if r.max_score > 0)

        result_query = select(AssessmentResult).where(
            AssessmentResult.assessment_id == assessment_id,
            AssessmentResult.candidate_id == candidate_id,
        )
        existing_res = await db.execute(result_query)
        record = existing_res.scalar_one_or_none()

        if record:
            record.total_score = total_score
            record.problems_solved = problems_solved
        else:
            new_record = AssessmentResult(
                assessment_id=assessment_id,
                candidate_id=candidate_id,
                total_score=total_score,
                problems_solved=problems_solved,
                total_time_seconds=0,
            )
            db.add(new_record)

        await db.flush()

    @staticmethod
    async def get_submission_detail(
        db: AsyncSession, submission_id: str, user: User
    ) -> SubmissionDetailResponse:
        result = await db.execute(select(Submission).where(Submission.id == submission_id))
        sub = result.scalar_one_or_none()
        if not sub:
            raise NotFoundException(message=f"Submission '{submission_id}' not found")

        is_elevated = user.role in [RoleEnum.ADMIN, RoleEnum.RECRUITER]
        if not is_elevated and sub.candidate_id != user.id:
            raise ForbiddenException(message="Access to this submission is restricted")

        tc_results_data = []
        if sub.test_case_results:
            for item in sub.test_case_results:
                tc_results_data.append(
                    TestCaseRunResult(
                        test_case_id=item["test_case_id"],
                        is_hidden=item["is_hidden"],
                        passed=item["passed"],
                        execution_time_ms=item["execution_time_ms"],
                        score_awarded=item["score_awarded"],
                        max_score=item["max_score"],
                        stdout=item.get("stdout") if (not item["is_hidden"] or is_elevated) else None,
                        expected_output=item.get("expected_output") if (not item["is_hidden"] or is_elevated) else None,
                        error_message=item.get("error_message") if (not item["is_hidden"] or is_elevated) else None,
                    )
                )

        return SubmissionDetailResponse(
            id=sub.id,
            candidate_id=sub.candidate_id,
            problem_id=sub.problem_id,
            assessment_id=sub.assessment_id,
            language=sub.language,
            status=sub.status,
            score=sub.score,
            max_score=sub.max_score,
            execution_time_ms=sub.execution_time_ms,
            created_at=sub.created_at,
            code=sub.code,
            error_message=sub.error_message,
            test_case_results=tc_results_data,
        )

    @staticmethod
    async def list_submissions(
        db: AsyncSession,
        user: User,
        problem_id: Optional[str] = None,
        assessment_id: Optional[str] = None,
        status: Optional[SubmissionStatusEnum] = None,
        candidate_id: Optional[str] = None,
        sort_order: SortOrderEnum = SortOrderEnum.DESC,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedResult[SubmissionResponse]:
        query = select(Submission)

        if user.role == RoleEnum.CANDIDATE:
            query = query.where(Submission.candidate_id == user.id)
        elif candidate_id:
            query = query.where(Submission.candidate_id == candidate_id)

        if problem_id:
            query = query.where(Submission.problem_id == problem_id)
        if assessment_id:
            query = query.where(Submission.assessment_id == assessment_id)
        if status:
            query = query.where(Submission.status == status)

        order_col = Submission.created_at.asc() if sort_order == SortOrderEnum.ASC else Submission.created_at.desc()
        query = query.order_by(order_col)

        result = await paginate(db, query, page=page, page_size=page_size)
        result.items = [SubmissionResponse.model_validate(s) for s in result.items]
        return result

    @staticmethod
    async def run_sample(
        db: AsyncSession, data: RunSampleCodeRequest
    ) -> SampleExecutionResult:
        prob_res = await db.execute(select(Problem).where(Problem.id == data.problem_id))
        problem = prob_res.scalar_one_or_none()
        if not problem:
            raise NotFoundException(message=f"Problem '{data.problem_id}' not found")

        input_text = data.custom_input if data.custom_input is not None else problem.sample_input
        expected_out = problem.sample_output if data.custom_input is None else None

        exec_res = await CodeExecutor.run(
            language=data.language,
            source_code=data.code,
            stdin_input=input_text,
            time_limit_ms=problem.time_limit_ms,
            memory_limit_mb=problem.memory_limit_mb,
        )

        norm_actual = CodeExecutor.normalize_output(exec_res.stdout)
        norm_expected = CodeExecutor.normalize_output(expected_out) if expected_out is not None else None

        passed = False
        if exec_res.status == SubmissionStatusEnum.ACCEPTED and norm_expected is not None:
            passed = (norm_actual == norm_expected)

        return SampleExecutionResult(
            status=exec_res.status if (passed or norm_expected is None) else SubmissionStatusEnum.WRONG_ANSWER,
            stdout=norm_actual,
            stderr=exec_res.stderr,
            execution_time_ms=exec_res.execution_time_ms,
            expected_output=norm_expected,
            passed=passed,
            error_message=exec_res.error_message,
        )
