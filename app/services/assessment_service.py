from datetime import datetime
from typing import Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.assessment import Assessment, AssessmentProblem
from app.models.enums import AssessmentStatusEnum, RoleEnum
from app.models.problem import Problem
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentDetailResponse,
    AssessmentProblemAdd,
    AssessmentProblemResponse,
    AssessmentResponse,
    AssessmentUpdate,
)
from app.schemas.common import SortOrderEnum
from app.schemas.problem import ProblemResponse
from app.utils.pagination import PaginatedResult, paginate


class AssessmentService:
    @staticmethod
    async def create_assessment(
        db: AsyncSession, recruiter: User, data: AssessmentCreate
    ) -> AssessmentDetailResponse:
        if data.end_time <= data.start_time:
            raise BadRequestException(message="End time must be after start time")

        assessment = Assessment(
            recruiter_id=recruiter.id,
            title=data.title.strip(),
            description=data.description.strip(),
            start_time=data.start_time,
            end_time=data.end_time,
            duration_minutes=data.duration_minutes,
            passing_score=data.passing_score,
            status=data.status,
        )
        db.add(assessment)
        await db.flush()

        if data.problems:
            for item in data.problems:
                prob_res = await db.execute(select(Problem.id).where(Problem.id == item.problem_id))
                if not prob_res.scalar_one_or_none():
                    raise NotFoundException(message=f"Problem '{item.problem_id}' not found")

                link = AssessmentProblem(
                    assessment_id=assessment.id,
                    problem_id=item.problem_id,
                    order_index=item.order_index,
                    points=item.points,
                )
                db.add(link)

            await db.flush()

        await db.refresh(assessment)
        return await AssessmentService.get_assessment_detail(db, assessment.id, recruiter)

    @staticmethod
    async def get_assessment_detail(
        db: AsyncSession, assessment_id: str, user: Optional[User] = None
    ) -> AssessmentDetailResponse:
        query = (
            select(Assessment)
            .where(Assessment.id == assessment_id)
            .options(
                selectinload(Assessment.problems).selectinload(AssessmentProblem.problem)
            )
        )
        result = await db.execute(query)
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise NotFoundException(message=f"Assessment '{assessment_id}' not found")

        is_elevated = user is not None and user.role in [RoleEnum.ADMIN, RoleEnum.RECRUITER]
        if assessment.status == AssessmentStatusEnum.DRAFT and not is_elevated:
            raise NotFoundException(message="Assessment is not currently published")

        problems_list = [
            AssessmentProblemResponse(
                problem_id=p.problem_id,
                order_index=p.order_index,
                points=p.points,
                problem=ProblemResponse.model_validate(p.problem),
            )
            for p in sorted(assessment.problems, key=lambda x: x.order_index)
        ]

        return AssessmentDetailResponse(
            id=assessment.id,
            recruiter_id=assessment.recruiter_id,
            title=assessment.title,
            description=assessment.description,
            start_time=assessment.start_time,
            end_time=assessment.end_time,
            duration_minutes=assessment.duration_minutes,
            passing_score=assessment.passing_score,
            status=assessment.status,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
            problems=problems_list,
        )

    @staticmethod
    async def list_assessments(
        db: AsyncSession,
        search: Optional[str] = None,
        status: Optional[AssessmentStatusEnum] = None,
        sort_by: str = "start_time",
        sort_order: SortOrderEnum = SortOrderEnum.DESC,
        page: int = 1,
        page_size: int = 10,
        user: Optional[User] = None,
    ) -> PaginatedResult[AssessmentResponse]:
        query = select(Assessment)

        is_elevated = user is not None and user.role in [RoleEnum.ADMIN, RoleEnum.RECRUITER]
        if not is_elevated:
            query = query.where(Assessment.status == AssessmentStatusEnum.PUBLISHED)
        elif status:
            query = query.where(Assessment.status == status)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Assessment.title.ilike(pattern),
                    Assessment.description.ilike(pattern),
                )
            )

        sort_map = {
            "created_at": Assessment.created_at,
            "title": Assessment.title,
            "end_time": Assessment.end_time,
        }
        sort_col = sort_map.get(sort_by, Assessment.start_time)
        query = query.order_by(sort_col.asc() if sort_order == SortOrderEnum.ASC else sort_col.desc())

        result = await paginate(db, query, page=page, page_size=page_size)
        result.items = [AssessmentResponse.model_validate(a) for a in result.items]
        return result

    @staticmethod
    async def update_assessment(
        db: AsyncSession, assessment_id: str, data: AssessmentUpdate, user: User
    ) -> AssessmentResponse:
        result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise NotFoundException(message=f"Assessment '{assessment_id}' not found")

        if user.role != RoleEnum.ADMIN and assessment.recruiter_id != user.id:
            raise ForbiddenException(message="You can only edit assessments you created")

        if data.title is not None:
            assessment.title = data.title.strip()
        if data.description is not None:
            assessment.description = data.description.strip()
        if data.start_time is not None:
            assessment.start_time = data.start_time
        if data.end_time is not None:
            assessment.end_time = data.end_time
        if data.duration_minutes is not None:
            assessment.duration_minutes = data.duration_minutes
        if data.passing_score is not None:
            assessment.passing_score = data.passing_score
        if data.status is not None:
            assessment.status = data.status

        if assessment.end_time <= assessment.start_time:
            raise BadRequestException(message="End time must be after start time")

        await db.flush()
        await db.refresh(assessment)
        return AssessmentResponse.model_validate(assessment)

    @staticmethod
    async def add_problem(
        db: AsyncSession, assessment_id: str, data: AssessmentProblemAdd, user: User
    ) -> None:
        result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
        assessment = result.scalar_one_or_none()
        if not assessment:
            raise NotFoundException(message=f"Assessment '{assessment_id}' not found")

        if user.role != RoleEnum.ADMIN and assessment.recruiter_id != user.id:
            raise ForbiddenException(message="You can only modify assessments you created")

        prob_res = await db.execute(select(Problem.id).where(Problem.id == data.problem_id))
        if not prob_res.scalar_one_or_none():
            raise NotFoundException(message=f"Problem '{data.problem_id}' not found")

        existing = await db.execute(
            select(AssessmentProblem).where(
                AssessmentProblem.assessment_id == assessment_id,
                AssessmentProblem.problem_id == data.problem_id,
            )
        )
        link = existing.scalar_one_or_none()

        if link:
            link.order_index = data.order_index
            link.points = data.points
        else:
            link = AssessmentProblem(
                assessment_id=assessment_id,
                problem_id=data.problem_id,
                order_index=data.order_index,
                points=data.points,
            )
            db.add(link)

        await db.flush()

    @staticmethod
    async def remove_problem(
        db: AsyncSession, assessment_id: str, problem_id: str, user: User
    ) -> None:
        result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
        assessment = result.scalar_one_or_none()
        if not assessment:
            raise NotFoundException(message=f"Assessment '{assessment_id}' not found")

        if user.role != RoleEnum.ADMIN and assessment.recruiter_id != user.id:
            raise ForbiddenException(message="You can only modify assessments you created")

        link_res = await db.execute(
            select(AssessmentProblem).where(
                AssessmentProblem.assessment_id == assessment_id,
                AssessmentProblem.problem_id == problem_id,
            )
        )
        link = link_res.scalar_one_or_none()
        if not link:
            raise NotFoundException(message="Problem is not associated with this assessment")

        await db.delete(link)
        await db.flush()

    @staticmethod
    async def delete_assessment(db: AsyncSession, assessment_id: str, user: User) -> None:
        result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
        assessment = result.scalar_one_or_none()
        if not assessment:
            raise NotFoundException(message=f"Assessment '{assessment_id}' not found")

        if user.role != RoleEnum.ADMIN and assessment.recruiter_id != user.id:
            raise ForbiddenException(message="You can only delete assessments you created")

        await db.delete(assessment)
        await db.flush()
