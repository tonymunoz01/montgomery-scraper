from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.models.scraping_log import ScrapingLog
from app.schemas.scraping_log import ScrapingLog as ScrapingLogSchema

router = APIRouter()

@router.get("/", response_model=List[ScrapingLogSchema])
def get_scraping_logs(db: Session = Depends(get_db)):
    """
    Get all scraping logs from the database
    """
    try:
        logs = db.query(ScrapingLog).all()
        return logs
    except Exception as e:
        logger.error(f"Error fetching scraping logs: {e}")
        raise HTTPException(status_code=500, detail="Error fetching scraping logs") 