from sqlalchemy import Column, String, Date, DateTime
from sqlalchemy.sql import func
from app.core.base import Base

class MontgomeryProbateCase(Base):
    __tablename__ = "montgomery_probate_cases"

    id = Column(String, primary_key=True, index=True)
    decedent_name = Column(String, index=True)
    filing_date = Column(Date)
    case_number = Column(String, unique=True, index=True)
    source_url = Column(String)
    county = Column(String)
    case_status = Column(String)
    property_address = Column(String)
    fiduciary_name = Column(String)
    fiduciary_address = Column(String)
    fiduciary_city = Column(String)
    fiduciary_zip = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())