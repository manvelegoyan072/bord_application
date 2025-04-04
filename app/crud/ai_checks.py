from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_checks import AICheck

async def create_ai_check(db: AsyncSession, tender_id: int, ai_status: str, ai_response: str):
    db_check = AICheck(tender_id=tender_id, ai_status=ai_status, ai_response=ai_response)
    db.add(db_check)
    await db.commit()
    await db.refresh(db_check)
    return db_check