from typing import List
from pydantic import BaseModel, ConfigDict


class LeaderboardEntryResponse(BaseModel):
    rank: int
    candidate_id: str
    candidate_name: str
    total_score: int
    problems_solved: int
    total_time_seconds: int

    model_config = ConfigDict(from_attributes=True)


class LeaderboardResponse(BaseModel):
    assessment_id: str
    assessment_title: str
    total_candidates: int
    entries: List[LeaderboardEntryResponse]
