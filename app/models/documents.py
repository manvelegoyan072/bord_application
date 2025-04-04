from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint('tender_id', 'file_name', name='uq_tender_file'),)

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    tender_id = Column(String, ForeignKey("tenders.external_id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    storage_location = Column(String, default="s3")
    status = Column(String, default="pending")
    tender = relationship("Tender", back_populates="docs")



