import re
from datetime import datetime
from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, NotFoundException
from app.models.enums import DifficultyEnum, RoleEnum
from app.models.problem import Problem
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.common import SortOrderEnum
from app.schemas.problem import (
    ProblemAdminDetailResponse,
    ProblemCreate,
    ProblemDetailResponse,
    ProblemResponse,
    ProblemUpdate,
)
from app.schemas.test_case import TestCasePublicResponse, TestCaseResponse
from app.utils.pagination import PaginatedResult, paginate


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[\s_-]+", "-", text).strip("-")


class ProblemService:
    @staticmethod
    async def create_problem(db: AsyncSession, data: ProblemCreate) -> ProblemResponse:
        base_slug = slugify(data.title)
        slug = base_slug
        counter = 1

        while True:
            existing = await db.execute(select(Problem.id).where(Problem.slug == slug))
            if not existing.scalar_one_or_none():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        problem = Problem(
            title=data.title.strip(),
            slug=slug,
            description=data.description.strip(),
            difficulty=data.difficulty,
            category=data.category.strip(),
            time_limit_ms=data.time_limit_ms,
            memory_limit_mb=data.memory_limit_mb,
            sample_input=data.sample_input,
            sample_output=data.sample_output,
            boilerplate_code=data.boilerplate_code,
            is_published=data.is_published,
        )

        db.add(problem)
        await db.flush()
        await db.refresh(problem)
        return ProblemResponse.model_validate(problem)

    @staticmethod
    async def get_problem_detail(
        db: AsyncSession, identifier: str, user: Optional[User] = None
    ) -> ProblemDetailResponse:
        query = (
            select(Problem)
            .where(or_(Problem.id == identifier, Problem.slug == identifier))
            .options(selectinload(Problem.test_cases))
        )
        result = await db.execute(query)
        problem = result.scalar_one_or_none()

        if not problem:
            raise NotFoundException(message=f"Problem '{identifier}' not found")

        is_elevated = user is not None and user.role in [RoleEnum.ADMIN, RoleEnum.RECRUITER]
        if not problem.is_published and not is_elevated:
            raise NotFoundException(message="Problem is not currently available")

        public_cases = [
            TestCasePublicResponse.model_validate(tc)
            for tc in problem.test_cases
            if not tc.is_hidden
        ]

        if is_elevated:
            all_cases = [TestCaseResponse.model_validate(tc) for tc in problem.test_cases]
            return ProblemAdminDetailResponse(
                id=problem.id,
                title=problem.title,
                slug=problem.slug,
                description=problem.description,
                difficulty=problem.difficulty,
                category=problem.category,
                time_limit_ms=problem.time_limit_ms,
                memory_limit_mb=problem.memory_limit_mb,
                sample_input=problem.sample_input,
                sample_output=problem.sample_output,
                boilerplate_code=problem.boilerplate_code,
                is_published=problem.is_published,
                created_at=problem.created_at,
                updated_at=problem.updated_at,
                sample_test_cases=public_cases,
                all_test_cases=all_cases,
            )

        return ProblemDetailResponse(
            id=problem.id,
            title=problem.title,
            slug=problem.slug,
            description=problem.description,
            difficulty=problem.difficulty,
            category=problem.category,
            time_limit_ms=problem.time_limit_ms,
            memory_limit_mb=problem.memory_limit_mb,
            sample_input=problem.sample_input,
            sample_output=problem.sample_output,
            boilerplate_code=problem.boilerplate_code,
            is_published=problem.is_published,
            created_at=problem.created_at,
            updated_at=problem.updated_at,
            sample_test_cases=public_cases,
        )

    @staticmethod
    async def list_problems(
        db: AsyncSession,
        search: Optional[str] = None,
        difficulty: Optional[DifficultyEnum] = None,
        category: Optional[str] = None,
        is_published: Optional[bool] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: SortOrderEnum = SortOrderEnum.DESC,
        page: int = 1,
        page_size: int = 10,
        user: Optional[User] = None,
    ) -> PaginatedResult[ProblemResponse]:
        query = select(Problem)

        is_elevated = user is not None and user.role in [RoleEnum.ADMIN, RoleEnum.RECRUITER]
        if not is_elevated:
            query = query.where(Problem.is_published == True)
        elif is_published is not None:
            query = query.where(Problem.is_published == is_published)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Problem.title.ilike(pattern),
                    Problem.slug.ilike(pattern),
                    Problem.category.ilike(pattern),
                )
            )

        if difficulty:
            query = query.where(Problem.difficulty == difficulty)
        if category:
            query = query.where(Problem.category.ilike(f"%{category.strip()}%"))
        if created_after:
            query = query.where(Problem.created_at >= created_after)
        if created_before:
            query = query.where(Problem.created_at <= created_before)

        sort_map = {
            "title": Problem.title,
            "difficulty": Problem.difficulty,
            "category": Problem.category,
            "time_limit_ms": Problem.time_limit_ms,
        }
        sort_column = sort_map.get(sort_by, Problem.created_at)
        query = query.order_by(sort_column.asc() if sort_order == SortOrderEnum.ASC else sort_column.desc())

        result = await paginate(db, query, page=page, page_size=page_size)
        result.items = [ProblemResponse.model_validate(p) for p in result.items]
        return result

    @staticmethod
    async def update_problem(
        db: AsyncSession, problem_id: str, data: ProblemUpdate
    ) -> ProblemResponse:
        result = await db.execute(select(Problem).where(Problem.id == problem_id))
        problem = result.scalar_one_or_none()

        if not problem:
            raise NotFoundException(message=f"Problem '{problem_id}' not found")

        if data.title is not None and data.title.strip() != problem.title:
            problem.title = data.title.strip()
            base_slug = slugify(data.title)
            slug = base_slug
            counter = 1
            while True:
                existing = await db.execute(
                    select(Problem.id).where(
                        Problem.slug == slug, Problem.id != problem_id
                    )
                )
                if not existing.scalar_one_or_none():
                    break
                slug = f"{base_slug}-{counter}"
                counter += 1
            problem.slug = slug

        if data.description is not None:
            problem.description = data.description.strip()
        if data.difficulty is not None:
            problem.difficulty = data.difficulty
        if data.category is not None:
            problem.category = data.category.strip()
        if data.time_limit_ms is not None:
            problem.time_limit_ms = data.time_limit_ms
        if data.memory_limit_mb is not None:
            problem.memory_limit_mb = data.memory_limit_mb
        if data.sample_input is not None:
            problem.sample_input = data.sample_input
        if data.sample_output is not None:
            problem.sample_output = data.sample_output
        if data.boilerplate_code is not None:
            problem.boilerplate_code = data.boilerplate_code
        if data.is_published is not None:
            problem.is_published = data.is_published

        await db.flush()
        await db.refresh(problem)
        return ProblemResponse.model_validate(problem)

    @staticmethod
    async def delete_problem(db: AsyncSession, problem_id: str) -> None:
        result = await db.execute(select(Problem).where(Problem.id == problem_id))
        problem = result.scalar_one_or_none()

        if not problem:
            raise NotFoundException(message=f"Problem '{problem_id}' not found")

        await db.delete(problem)
        await db.flush()
