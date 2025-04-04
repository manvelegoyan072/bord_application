from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class FilterBase(BaseModel):
    title: str
    description: Optional[str] = None
    type: str
    calculation: str
    parent_id: Optional[int] = None
    priority: int
    active: bool = True
    provider_id: Optional[int] = None
    user_id: Optional[int] = None
    condition: Optional[str] = None
    success_action: Optional[int] = None
    formula: Optional[str] = None
    formula_target: Optional[str] = None

class FilterCreate(FilterBase):
    pass

class Filter(FilterBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class FilterShort(BaseModel):
    id: int
    name: str
    type: str
    active: bool

class FilterListResponse(BaseModel):
    filters: List[FilterShort]
    total: int
    page: int
    per_page: int