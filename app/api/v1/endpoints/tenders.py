from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, asc, desc
from sqlalchemy.orm import selectinload
from app.schemas.tender_request import IncomingTenderData, TenderResponse, TenderRequest
from app.schemas.tenders import TenderListResponse, TenderDetail
from app.services.tender_service import process_and_save_tender
from app.crud.tenders import get_tender_by_id, save_tender
from app.db.database import get_db
from app.core.logging_config import logger
from app.models.tenders import Tender
from app.models.ai_checks import AICheck
from typing import Optional

router = APIRouter()

@router.post(
    "/incoming_data",
    response_model=TenderResponse,
    summary="Создание новых тендеров",
    description="Принимает список групп тендеров и сразу возвращает подтверждение принятия, запуская обработку в фоне.",
    responses={
        200: {"description": "Запрос успешно принят", "content": {
            "application/json": {"example": {"status": "success", "tender_id": "IS49226739", "state": "RECEIVED"}}}},
        409: {"description": "Тендер с таким ID уже существует", "content": {"application/json": {"example": {
            "detail": {"message": "Tender with id 'IS49226739' already exists", "tender_id": "IS49226739"}}}}},
        422: {"description": "Ошибка валидации входных данных",
              "content": {"application/json": {"example": {"detail": "Invalid tender data"}}}}
    }
)
async def incoming_data(
        data: IncomingTenderData,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db)
):
    logger.info("Received incoming tender data")
    try:
        for group in data.data:
            for tender_data in group.requests:
                logger.info(f"Processing tender {tender_data.id}, initial state: {tender_data.state}")
                existing_tender = await get_tender_by_id(db, tender_data.id)
                if existing_tender:
                    logger.warning(f"Tender {tender_data.id} already exists")
                    raise HTTPException(
                        status_code=409,
                        detail={"message": f"Tender with id '{tender_data.id}' already exists",
                                "tender_id": tender_data.id}
                    )


                db_tender = await save_tender(db, tender_data, group.type)
                if not db_tender:
                    logger.error(f"Failed to initially save tender {tender_data.id}")
                    raise HTTPException(status_code=500, detail="Failed to save tender")


                background_tasks.add_task(process_and_save_tender, tender_data, group.type)


                response = TenderResponse(status="success", tender_id=tender_data.id, state="RECEIVED")
                logger.info(f"Returning success response: {response.dict()}")
                return response

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error accepting tender data: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get(
    "/{tender_id}/status",
    response_model=TenderResponse,
    summary="Получение статуса тендера",
    description="Возвращает текущее состояние тендера по его ID.",
    responses={
        200: {"description": "Статус тендера", "content": {
            "application/json": {"example": {"status": "success", "tender_id": "IS49226739", "state": "COMPLETED"}}}},
        404: {"description": "Тендер не найден", "content": {
            "application/json": {"example": {"status": "error", "tender_id": "IS49226739", "state": "NOT_FOUND"}}}}
    }
)
async def get_tender_status(tender_id: str, db: AsyncSession = Depends(get_db)):
    logger.info(f"Fetching status for tender {tender_id}")
    result = await db.execute(select(Tender).filter(Tender.external_id == tender_id))
    tender = result.scalars().first()
    if tender:
        logger.info(f"Tender {tender_id} found with state: {tender.state}")
        return TenderResponse(status="success", tender_id=tender_id, state=tender.state)
    logger.warning(f"Tender {tender_id} not found")
    return TenderResponse(status="error", tender_id=tender_id, state="NOT_FOUND")

@router.get("/", response_model=TenderListResponse)
async def get_tenders(
        page: int = Query(1, ge=1, description="Номер страницы"),
        per_page: int = Query(20, ge=1, le=100, description="Количество записей на странице"),
        external_id: Optional[str] = Query(None, description="Фильтр по ID тендера"),
        type: Optional[str] = Query(None, description="Фильтр по типу"),
        state: Optional[str] = Query(None, description="Фильтр по состоянию"),
        created_at: Optional[str] = Query(None, description="Фильтр по дате создания (YYYY-MM-DD)"),
        sort_field: Optional[str] = Query("created_at",
                                          description="Поле для сортировки (external_id, type, state, created_at)"),
        sort_direction: Optional[str] = Query("desc", description="Направление сортировки (asc, desc)"),
        db: AsyncSession = Depends(get_db)
):
    logger.info(
        f"Fetching tenders list: page={page}, per_page={per_page}, filters={external_id, type, state, created_at}, sort={sort_field, sort_direction}")


    query = select(Tender)
    if external_id:
        query = query.where(Tender.external_id.ilike(f"%{external_id}%"))
    if type:
        query = query.where(Tender.type.ilike(f"%{type}%"))
    if state:
        query = query.where(Tender.state.ilike(f"%{state}%"))
    if created_at:
        query = query.where(func.date(Tender.created_at) == func.date(created_at))

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar()

    sort_options = {
        "external_id": Tender.external_id,
        "type": Tender.type,
        "state": Tender.state,
        "created_at": Tender.created_at,
    }
    if sort_field not in sort_options:
        raise HTTPException(status_code=400, detail="Invalid sort field")
    sort_column = sort_options[sort_field]
    query = query.order_by(asc(sort_column) if sort_direction == "asc" else desc(sort_column))

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    tenders = result.scalars().all()

    logger.info(f"Returning {len(tenders)} tenders, total={total}")
    return {"tenders": tenders, "total": total, "page": page, "per_page": per_page}

@router.get("/pumps", response_model=TenderListResponse)
async def get_pumps(
        page: int = Query(1, ge=1, description="Номер страницы"),
        per_page: int = Query(20, ge=1, le=100, description="Количество записей на странице"),
        external_id: Optional[str] = Query(None, description="Фильтр по ID тендера"),
        state: Optional[str] = Query(None, description="Фильтр по состоянию"),
        created_at: Optional[str] = Query(None, description="Фильтр по дате создания (YYYY-MM-DD)"),
        sort_field: Optional[str] = Query("created_at",
                                          description="Поле для сортировки (external_id, state, created_at)"),
        sort_direction: Optional[str] = Query("desc", description="Направление сортировки (asc, desc)"),
        db: AsyncSession = Depends(get_db)
):
    logger.info(
        f"Fetching pumps list: page={page}, per_page={per_page}, filters={external_id, state, created_at}, sort={sort_field, sort_direction}")


    query = select(Tender).where(Tender.type == "насосы")
    if external_id:
        query = query.where(Tender.external_id.ilike(f"%{external_id}%"))
    if state:
        query = query.where(Tender.state.ilike(f"%{state}%"))
    if created_at:
        query = query.where(func.date(Tender.created_at) == func.date(created_at))

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar()

    sort_options = {
        "external_id": Tender.external_id,
        "state": Tender.state,
        "created_at": Tender.created_at,
    }
    if sort_field not in sort_options:
        raise HTTPException(status_code=400, detail="Invalid sort field")
    sort_column = sort_options[sort_field]
    query = query.order_by(asc(sort_column) if sort_direction == "asc" else desc(sort_column))

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    tenders = result.scalars().all()

    logger.info(f"Returning {len(tenders)} pumps, total={total}")
    return {"tenders": tenders, "total": total, "page": page, "per_page": per_page}


@router.get("/{tender_id}", response_model=TenderDetail)
async def get_tender_detail(tender_id: str, db: AsyncSession = Depends(get_db)):
    logger.info(f"Fetching details for tender {tender_id}")


    result = await db.execute(
        select(Tender)
        .options(
            selectinload(Tender.lots),
            selectinload(Tender.docs),
        )
        .filter(Tender.external_id == tender_id)
    )
    tender = result.scalars().first()
    if not tender:
        logger.warning(f"Tender {tender_id} not found")
        raise HTTPException(status_code=404, detail="Tender not found")


    ai_check_result = await db.execute(
        select(AICheck)
        .filter(AICheck.tender_id == tender_id)
        .order_by(AICheck.checked_at.desc())
        .limit(1)
    )
    ai_check = ai_check_result.scalars().first()


    task_id = ai_check.task_id if ai_check else None
    ai_response = ai_check.ai_response if ai_check else None


    tender_data = TenderDetail.from_orm(tender)
    tender_data.task_id = task_id
    tender_data.ai_response = ai_response

    logger.info(f"Tender {tender_id} found with {len(tender.lots)} lots and {len(tender.docs)} documents")
    return tender_data