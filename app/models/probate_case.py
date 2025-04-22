from sqlalchemy import Column, String, Date, DateTime
from sqlalchemy.sql import func
from app.core.base import Base

class ProbateCase(Base):
    __tablename__ = "probate_cases"

    id = Column(String, primary_key=True, index=True)
    decedent_name = Column(String, nullable=False)
    filing_date = Column(Date, nullable=False)
    case_number = Column(String, nullable=False, unique=True)
    source_url = Column(String, nullable=False)
    county = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())