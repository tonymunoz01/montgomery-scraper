from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.base import Base

class ScrapingLog(Base):
    __tablename__ = "scraping_log"

    id = Column(String, primary_key=True, index=True)
    date_time = Column(DateTime, nullable=False)
    source = Column(String, nullable=False)
    total_records = Column(Integer, nullable=False)
    success_status = Column(Boolean, nullable=False)
    error_message = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 