from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tender_id = Column(String, ForeignKey("tenders.external_id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    customer_id = Column(Integer)
    initial_sum = Column(Numeric(15, 2))
    currency = Column(String)
    delivery_place = Column(String)
    delivery_term = Column(String)
    payment_term = Column(String)

    tender = relationship("Tender", back_populates="lots")