
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.bitrix import BitrixLeadCreate
from app.services.bitrix_service import export_to_bitrix
from app.crud.tenders import get_tender_by_id
from app.db.database import get_db
from app.core.logging_config import logger
from app.core.config import settings
import aiohttp

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def verify_token(token: str = Depends(oauth2_scheme)):

    if token != settings.KEPLER_API_TOKEN:
        logger.error(f"Invalid token provided: {token}")
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    logger.debug(f"Token verified successfully")
    return token

@router.get("/status")
async def bitrix_status():

    return {"message": "Bitrix endpoint is working"}

@router.post("/export/{tender_id}")
async def export_tender_to_bitrix(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verify_token)
):

    tender = await get_tender_by_id(db, tender_id)
    if not tender:
        logger.error(f"Tender {tender_id} not found")
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")

    success = await export_to_bitrix(tender, db)
    if success:
        return {"message": f"Tender {tender_id} successfully exported to Bitrix"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to export tender {tender_id} to Bitrix")

@router.post("/leads/create")
async def create_bitrix_lead(
    lead_data: BitrixLeadCreate,
    token: str = Depends(verify_token)
):

    headers = {"Content-Type": "application/json"}
    payload = {"fields": lead_data.fields}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{settings.BITRIX_WEBHOOK_URL}/crm.lead.add.json", json=payload, headers=headers
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                lead_id = result.get("result")
                logger.info(f"Lead created in Bitrix with ID {lead_id}")
                return {"message": f"Lead created successfully with ID {lead_id}", "lead_id": lead_id}
            else:
                error_text = await resp.text()
                logger.error(f"Failed to create lead in Bitrix: {resp.status}, {error_text}")
                raise HTTPException(status_code=resp.status, detail=f"Failed to create lead: {error_text}")