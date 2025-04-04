from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime



class Money(BaseModel):
    price: float
    currency: str

    class Config:
        from_attributes = True

class Lot(BaseModel):
    title: str
    initial_sum: Money
    delivery_place: Optional[str] = None
    delivery_term: Optional[str] = None
    payment_term: Optional[str] = None

    class Config:
        from_attributes = True

class Document(BaseModel):
    file_name: str
    url: str

    class Config:
        from_attributes = True

class Etp(BaseModel):
    code: str
    name: str
    url: str

    class Config:
        from_attributes = True

class TenderRequest(BaseModel):
    id: str
    title: str
    notification_number: Optional[str] = None
    notification_type: Optional[str] = None
    organizer: Dict[str, Any] = {}
    initial_sum: Money
    application_deadline: Optional[datetime] = None
    etp: Optional[Etp] = None
    kontur_link: Optional[str] = None
    publication_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    docs: List[Document] = []
    lots: List[Lot] = []
    selection_method: Optional[str] = None
    smp: Optional[str] = None
    state: str = "RECEIVED"

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class TenderGroup(BaseModel):
    type: str
    requests: List[TenderRequest]

class IncomingTenderData(BaseModel):
    data: List[TenderGroup]


class TenderResponse(BaseModel):
    status: str
    tender_id: Optional[str] = None
    state: str

    class Config:
        from_attributes = True