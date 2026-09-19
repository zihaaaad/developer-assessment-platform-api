from fastapi import APIRouter

from app.api.v1.endpoints import (
    assessments,
    auth,
    leaderboard,
    problems,
    submissions,
    test_cases,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Profile"])
api_router.include_router(users.router, prefix="/users", tags=["User Management (Admin)"])
api_router.include_router(problems.router, prefix="/problems", tags=["Coding Problems"])
api_router.include_router(test_cases.router, tags=["Test Cases"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments & Contests"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["Code Execution & Submissions"])
api_router.include_router(leaderboard.router, prefix="/leaderboard", tags=["Leaderboards"])
