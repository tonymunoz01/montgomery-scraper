from sqlalchemy import Column, String, Date, DateTime, JSON
from sqlalchemy.sql import func
from app.core.base import Base

class MontgomeryForeclosureCase(Base):
    __tablename__ = "montgomery_foreclosure_cases"
    id = Column(String, primary_key=True, index=True)
    property_address = Column(String, index=True)
    filing_date = Column(Date)
    case_id = Column(String, unique=True, index=True)
    source_url = Column(String)
    county = Column(String)
    case_status = Column(String)
    filing_type = Column(String)
    plaintiff = Column(String)
    defendants = Column(JSON)
    parcel_number = Column(String)
    case_filing_id = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 