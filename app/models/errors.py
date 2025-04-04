from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey
from app.models.base import Base

class Error(Base):
    __tablename__ = "errors"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(String, ForeignKey("tenders.external_id", ondelete="CASCADE"), nullable=False)
    module = Column(String, nullable=False)
    error_message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())