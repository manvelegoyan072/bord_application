from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.models.base import Base

class AICheck(Base):
    __tablename__ = "ai_checks"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(String, ForeignKey("tenders.external_id", ondelete="CASCADE"), nullable=False)
    ai_status = Column(String, nullable=False)
    ai_response = Column(Text)
    task_id = Column(Text)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())