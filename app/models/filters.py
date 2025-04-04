from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base

class Filter(Base):
    __tablename__ = "filters"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String, nullable=False)
    condition = Column(Text, nullable=True)
    calculation = Column(String, nullable=False)
    formula_target = Column(Text, nullable=True)
    formula = Column(Text, nullable=True)
    user_id = Column(Integer)
    provider_id = Column(Integer)
    priority = Column(Integer, nullable=False)
    parent_id = Column(Integer, ForeignKey("filters.id"), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    success_action = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)