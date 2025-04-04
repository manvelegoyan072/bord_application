from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schemas.document import Document
from app.schemas.lot import Lot

class TenderDetail(BaseModel):
    external_id: str
    title: str
    notification_number: Optional[str] = None
    notification_type: Optional[str] = None
    organizer: Dict[str, Any] = {}
    initial_price: Optional[float] = None
    currency: Optional[str] = None
    application_deadline: Optional[datetime] = None
    etp_code: Optional[str] = None
    etp_name: Optional[str] = None
    etp_url: Optional[str] = None
    kontur_link: Optional[str] = None
    publication_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    selection_method: Optional[str] = None
    smp: Optional[str] = None
    status: Optional[str] = None
    type: str
    created_at: datetime
    state: str
    lots: List[Lot] = []
    documents: List[Document] = []
    task_id: Optional[str] = None
    ai_response: Optional[str] = None

    class Config:
        from_attributes = True


class TenderShort(BaseModel):
    external_id: str
    type: str
    state: str
    created_at: datetime

    class Config:
        from_attributes = True

class TenderListResponse(BaseModel):
    tenders: List[TenderShort]
    total: int
    page: int
    per_page: int

    class Config:
        from_attributes = True