from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.user import User
from app.schemas.leaderboard import LeaderboardEntryResponse, LeaderboardResponse


class LeaderboardService:
    @staticmethod
    async def get_assessment_leaderboard(
        db: AsyncSession, assessment_id: str
    ) -> LeaderboardResponse:
        assess_res = await db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = assess_res.scalar_one_or_none()

        if not assessment:
            raise NotFoundException(message=f"Assessment '{assessment_id}' not found")

        query = (
            select(AssessmentResult)
            .where(AssessmentResult.assessment_id == assessment_id)
            .options(selectinload(AssessmentResult.candidate))
            .order_by(
                AssessmentResult.total_score.desc(),
                AssessmentResult.problems_solved.desc(),
                AssessmentResult.total_time_seconds.asc(),
            )
        )
        results = await db.execute(query)
        result_records = results.scalars().all()

        entries: List[LeaderboardEntryResponse] = []
        for index, record in enumerate(result_records, start=1):
            record.rank = index
            entries.append(
                LeaderboardEntryResponse(
                    rank=index,
                    candidate_id=record.candidate_id,
                    candidate_name=record.candidate.name,
                    total_score=record.total_score,
                    problems_solved=record.problems_solved,
                    total_time_seconds=record.total_time_seconds,
                )
            )

        return LeaderboardResponse(
            assessment_id=assessment.id,
            assessment_title=assessment.title,
            total_candidates=len(entries),
            entries=entries,
        )
