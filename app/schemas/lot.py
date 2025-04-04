from pydantic import BaseModel
from typing import Optional

class Lot(BaseModel):
    id: Optional[int] = None
    tender_id: str
    title: str
    initial_sum: Optional[float] = None
    currency: Optional[str] = None
    delivery_place: Optional[str] = None
    delivery_term: Optional[str] = None
    payment_term: Optional[str] = None

    class Config:
        from_attributes = True