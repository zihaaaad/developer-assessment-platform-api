from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import StandardResponse
from app.schemas.leaderboard import LeaderboardResponse
from app.services.leaderboard_service import LeaderboardService
from app.utils.api_response import make_response

router = APIRouter()


@router.get(
    "/assessments/{assessment_id}",
    response_model=StandardResponse[LeaderboardResponse],
    summary="Get real-time ranked leaderboard for an assessment",
)
async def get_assessment_leaderboard(
    assessment_id: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[LeaderboardResponse]:
    leaderboard = await LeaderboardService.get_assessment_leaderboard(db, assessment_id)
    return make_response(data=leaderboard, message="Leaderboard retrieved successfully")
