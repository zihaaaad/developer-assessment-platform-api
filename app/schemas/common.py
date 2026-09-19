from typing import Generic, List, Optional, TypeVar
import enum
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class SortOrderEnum(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"


class PaginationMeta(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    page_size: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Data retrieved successfully"
    pagination: PaginationMeta
    data: List[T]


class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Operation successful"
    data: Optional[T] = None


class MessageResponse(BaseModel):
    success: bool = True
    message: str
