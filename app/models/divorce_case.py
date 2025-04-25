from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class DivorceCase(Base):
    __tablename__ = "divorce_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, unique=True, index=True)
    case_number = Column(String)
    plaintiff = Column(String)
    defendant = Column(String)
    filing_date = Column(String)
    status = Column(String)
    county = Column(String)
    property_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 