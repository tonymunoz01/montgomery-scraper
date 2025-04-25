from sqlalchemy import Column, String, Date, DateTime, JSON
from sqlalchemy.sql import func
from app.core.base import Base

class ForeclosureCase(Base):
    __tablename__ = "foreclosure_cases"
    case_id = Column(String, primary_key=True, index=True)
    filing_type = Column(String)
    filing_date = Column(Date)
    status = Column(String)
    plaintiff = Column(String)
    defendants = Column(JSON)
    parcel_number = Column(String)
    case_filing_id = Column(String)
    county = Column(String)
    property_address = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 