from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.filters import Filter

async def get_active_filters(db: AsyncSession, filter_type: str = "tender") -> List[Filter]:
    result = await db.execute(
        select(Filter).filter_by(active=True, type=filter_type).order_by(Filter.priority)
    )
    return result.scalars().all()

async def get_filter(db: AsyncSession, filter_id: int) -> Filter:
    result = await db.execute(select(Filter).filter_by(id=filter_id))
    return result.scalars().first()

async def create_filter(db: AsyncSession, filter_data: 'FilterCreate') -> Filter:
    db_filter = Filter(**filter_data.dict())
    db.add(db_filter)
    await db.commit()
    await db.refresh(db_filter)
    return db_filter

async def update_filter(db: AsyncSession, filter_id: int, filter_data: dict) -> Filter:
    db_filter = await get_filter(db, filter_id)
    if db_filter:
        for key, value in filter_data.items():
            setattr(db_filter, key, value)
        await db.commit()
        await db.refresh(db_filter)
    return db_filter

async def delete_filter(db: AsyncSession, filter_id: int) -> Filter:
    db_filter = await get_filter(db, filter_id)
    if db_filter:
        await db.delete(db_filter)
        await db.commit()
    return db_filter