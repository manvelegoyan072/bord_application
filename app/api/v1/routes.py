from fastapi import APIRouter
from app.api.v1.endpoints import ai, bitrix, documents, filters, health, tenders, users

router = APIRouter(prefix="/v1")

router.include_router(ai.router, prefix="/ai", tags=["AI"])
router.include_router(bitrix.router, prefix="/bitrix", tags=["Bitrix"])
router.include_router(documents.router, prefix="/documents", tags=["Documents"])
router.include_router(filters.router, prefix="/filters", tags=["Filters"])
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(tenders.router, prefix="/tenders", tags=["Tenders"])
router.include_router(users.router, prefix="/users", tags=["Users"])
