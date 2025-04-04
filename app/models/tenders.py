from sqlalchemy import Column, String, Numeric, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base

class Tender(Base):
    __tablename__ = "tenders"

    external_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    notification_number = Column(String)
    notification_type = Column(String)
    organizer = Column(JSONB)  # Хранит fullName, inn, phone, email и т.д.
    initial_price = Column(Numeric(15, 2))
    currency = Column(String)
    application_deadline = Column(DateTime(timezone=True))
    etp_code = Column(String)
    etp_name = Column(String)
    etp_url = Column(String)
    kontur_link = Column(String)
    publication_date = Column(DateTime(timezone=True))
    last_modified = Column(DateTime(timezone=True))
    selection_method = Column(String)
    smp = Column(String)
    status = Column(String, default="new")
    type = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    state = Column(String, nullable=False, default="RECEIVED")

    docs = relationship("Document", back_populates="tender")
    lots = relationship("Lot", back_populates="tender")