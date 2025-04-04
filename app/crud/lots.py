from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.lots import Lot as LotModel

async def create_lot(db: AsyncSession, tender_id: str, title: str, initial_sum: float, currency: str, delivery_place: str | None, delivery_term: str | None, payment_term: str | None):
    db_lot = LotModel(
        tender_id=tender_id,
        title=title,
        initial_sum=initial_sum,
        currency=currency,
        delivery_place=delivery_place or "",
        delivery_term=delivery_term or "",
        payment_term=payment_term or ""
    )
    db.add(db_lot)
    await db.commit()
    await db.refresh(db_lot)
    return db_lot

async def get_lots_by_tender_id(db: AsyncSession, tender_id: str):
    result = await db.execute(select(LotModel).filter_by(tender_id=tender_id))
    return result.scalars().all()