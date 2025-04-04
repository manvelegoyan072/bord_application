from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def users_status():
    return {"message": "Users endpoint is working"}