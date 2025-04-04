from pydantic import BaseModel, Field
from typing import Dict, Any
class BitrixLeadCreate(BaseModel):
    fields: Dict[str, Any] = Field(..., description="Поля для создания лида в Bitrix")