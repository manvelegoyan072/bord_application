
from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def ai_status():
    return {"message": "AI endpoint is working"}