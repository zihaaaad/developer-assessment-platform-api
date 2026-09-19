from typing import Any, List, Optional
from fastapi.responses import JSONResponse
from app.schemas.common import PaginatedResponse, PaginationMeta, StandardResponse


def make_response(
    data: Optional[Any] = None,
    message: str = "Operation successful",
    status_code: int = 200,
) -> StandardResponse[Any]:
    return StandardResponse(
        success=True,
        message=message,
        data=data,
    )


def make_paginated_response(
    data: List[Any],
    pagination: PaginationMeta,
    message: str = "Data retrieved successfully",
) -> PaginatedResponse[Any]:
    return PaginatedResponse(
        success=True,
        message=message,
        pagination=pagination,
        data=data,
    )
