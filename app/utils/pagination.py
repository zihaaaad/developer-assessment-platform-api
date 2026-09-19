import math
from typing import Any, Generic, List, Sequence, TypeVar
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.schemas.common import PaginationMeta

T = TypeVar("T")


class PaginatedResult(Generic[T]):
    def __init__(
        self,
        items: Sequence[T],
        total_items: int,
        page: int,
        page_size: int,
    ):
        self.items = items
        self.total_items = total_items
        self.current_page = page
        self.page_size = page_size
        self.total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
        self.has_next = self.current_page < self.total_pages
        self.has_prev = self.current_page > 1

    @property
    def meta(self) -> PaginationMeta:
        return PaginationMeta(
            total_items=self.total_items,
            total_pages=self.total_pages,
            current_page=self.current_page,
            page_size=self.page_size,
            has_next=self.has_next,
            has_prev=self.has_prev,
        )


async def paginate(
    session: AsyncSession,
    query: Select,
    page: int = 1,
    page_size: int = 10,
) -> PaginatedResult[Any]:
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 10
    if page_size > 100:
        page_size = 100

    count_subquery = query.order_by(None).subquery()
    count_query = select(func.count()).select_from(count_subquery)
    total_items_res = await session.execute(count_query)
    total_items = total_items_res.scalar() or 0

    offset = (page - 1) * page_size
    paginated_query = query.offset(offset).limit(page_size)
    items_res = await session.execute(paginated_query)
    items = items_res.scalars().all()

    return PaginatedResult(
        items=items,
        total_items=total_items,
        page=page,
        page_size=page_size,
    )
