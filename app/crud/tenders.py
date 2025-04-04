from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.models.tenders import Tender
from app.schemas.tender_request import TenderRequest, Etp
from app.crud.documents import save_documents, get_documents_by_tender_id
from app.crud.lots import create_lot, get_lots_by_tender_id
from app.core.logging_config import logger

async def get_tender_by_id(db: AsyncSession, tender_id: str) -> Tender | None:
    """Получает тендер по external_id с предварительной загрузкой связанных данных."""
    try:
        result = await db.execute(
            select(Tender)
            .options(joinedload(Tender.docs), joinedload(Tender.lots))  # Добавляем подгрузку связанных данных
            .filter(Tender.external_id == tender_id)
        )
        tender = result.scalars().first()
        if not tender:
            logger.warning(f"Tender with external_id {tender_id} not found")
        return tender
    except Exception as e:
        logger.error(f"Error fetching tender with external_id {tender_id}: {str(e)}")
        raise

async def update_tender_status(db: AsyncSession, tender_id: str, status: str) -> Tender:
    tender = await get_tender_by_id(db, tender_id)
    if tender:
        tender.status = status
        await db.commit()
        await db.refresh(tender)
    return tender

async def save_tender(db: AsyncSession, tender: TenderRequest, type_name: str) -> Tender:
    try:
        db_tender = Tender(
            external_id=tender.id,
            title=tender.title,
            notification_number=tender.notification_number,
            notification_type=tender.notification_type,
            organizer=tender.organizer,
            initial_price=tender.initial_sum.price,
            currency=tender.initial_sum.currency,
            application_deadline=tender.application_deadline,
            etp_code=tender.etp.code if tender.etp else None,
            etp_name=tender.etp.name if tender.etp else None,
            etp_url=tender.etp.url if tender.etp else None,
            kontur_link=tender.kontur_link,
            publication_date=tender.publication_date,
            last_modified=tender.last_modified,
            selection_method=tender.selection_method,
            smp=tender.smp,
            type=type_name,
            state="RECEIVED"
        )
        db.add(db_tender)
        await db.commit()
        await db.refresh(db_tender)

        # Сохраняем документы и лоты в рамках одной транзакции
        if tender.docs:
            if not await save_documents(db, tender.id, tender.docs, tender.kontur_link):
                raise Exception("Failed to save documents")
        for lot in tender.lots:
            await create_lot(
                db,
                tender.id,
                lot.title,
                lot.initial_sum.price,
                lot.initial_sum.currency,
                lot.delivery_place,
                lot.delivery_term,
                lot.payment_term
            )
        await db.commit()
        return db_tender

    except Exception as e:
        logger.error(f"Error saving tender {tender.id}: {str(e)}")
        await db.rollback()
        return None

async def tender_to_schema(tender: Tender, db: AsyncSession) -> TenderRequest:
    docs = await get_documents_by_tender_id(db, tender.external_id)
    lots = await get_lots_by_tender_id(db, tender.external_id)
    etp = Etp(code=tender.etp_code, name=tender.etp_name, url=tender.etp_url) if tender.etp_code else None
    return TenderRequest(
        id=tender.external_id,
        title=tender.title,
        notification_number=tender.notification_number,
        notification_type=tender.notification_type,
        organizer=tender.organizer or {},
        initial_sum={"price": tender.initial_price, "currency": tender.currency},
        application_deadline=tender.application_deadline,
        publication_date=tender.publication_date,
        last_modified=tender.last_modified,
        etp=etp,
        kontur_link=tender.kontur_link,
        docs=docs,
        lots=lots,
        selection_method=tender.selection_method,
        smp=tender.smp
    )