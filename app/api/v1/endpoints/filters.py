from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.models.filters import Filter
from app.schemas.filters import FilterCreate, Filter as FilterSchema, FilterListResponse, FilterShort
from typing import Optional, List
from sqlalchemy import func

router = APIRouter()

@router.get("/", response_model=FilterListResponse)
async def get_filters(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    id_eq: Optional[int] = Query(None),
    name_cont: Optional[str] = Query(None),
    type_eq: Optional[str] = Query(None),
    active_eq: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(Filter)
    if id_eq:
        query = query.where(Filter.id == id_eq)
    if name_cont:
        query = query.where(Filter.title.ilike(f"%{name_cont}%"))
    if type_eq:
        query = query.where(Filter.type == type_eq)
    if active_eq is not None:
        query = query.where(Filter.active == active_eq)

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    filters = result.scalars().all()

    return {
        "filters": [{"id": f.id, "name": f.title, "type": f.type, "active": f.active} for f in filters],
        "total": total,
        "page": page,
        "per_page": per_page
    }

@router.get("/{filter_id}", response_model=FilterSchema)
async def get_filter_by_id(filter_id: int, db: AsyncSession = Depends(get_db)):
    filter_obj = await db.get(Filter, filter_id)
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    return filter_obj

@router.delete("/{filter_id}")
async def delete_filter(filter_id: int, db: AsyncSession = Depends(get_db)):
    filter_obj = await db.get(Filter, filter_id)
    if not filter_obj:
        raise HTTPException(status_code=404, detail="Filter not found")
    await db.delete(filter_obj)
    await db.commit()
    return {"status": "success"}

@router.post("/", response_model=FilterSchema)
async def create_filter(filter: FilterCreate, db: AsyncSession = Depends(get_db)):
    filter_data = filter.dict(exclude_unset=True)
    db_filter = Filter(**filter_data)
    db.add(db_filter)
    await db.commit()
    await db.refresh(db_filter)
    return db_filter

@router.put("/{filter_id}", response_model=FilterSchema)
async def update_filter(filter_id: int, filter: FilterCreate, db: AsyncSession = Depends(get_db)):

    db_filter = await db.get(Filter, filter_id)
    if not db_filter:
        raise HTTPException(status_code=404, detail="Filter not found")


    filter_data = filter.dict(exclude_unset=True)
    for key, value in filter_data.items():
        setattr(db_filter, key, value)


    db.add(db_filter)
    await db.commit()
    await db.refresh(db_filter)

    return db_filter