from sqlalchemy import Column, Integer, String, DateTime, JSON, Date, Text
from sqlalchemy.sql import func
from app.core.database import Base

class DivorceCase(Base):
    __tablename__ = "montgomery_divorce_cases"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, unique=True, index=True)
    petitioner_name = Column(String, index=True)
    respondent_name = Column(String, index=True)
    filing_date = Column(Date)
    source_url = Column(String)
    county = Column(String)
    case_status = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 