from sqlalchemy.ext.asyncio import AsyncSession
from app.models.errors import Error

async def log_tender_error(db: AsyncSession, tender_id: str, error_message: str):
    error = Error(tender_id=tender_id, module="tender_processing", error_message=error_message)
    db.add(error)
    await db.commit()