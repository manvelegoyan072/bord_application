from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def documents_status():
    return {"message": "Documents endpoint is working"}