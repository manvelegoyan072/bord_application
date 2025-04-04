from pydantic import BaseModel
from typing import Optional

class Document(BaseModel):
    id: Optional[int] = None
    tender_id: str
    file_name: str
    url: str
    storage_location: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True