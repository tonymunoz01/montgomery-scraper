from typing import List
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.core.database import get_db
from app.services.divorce_scraper import DivorceScraperService
from app.schemas.divorce_case import DivorceCase, DivorceCaseCreate

router = APIRouter()
divorce_scraper_service = DivorceScraperService()

@router.get("/", response_model=List[DivorceCase])
async def get_cases(db=Depends(get_db)):
    """
    Get all divorce cases from the database
    """
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM divorce_cases ORDER BY created_at DESC")
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching divorce cases: {e}")
        raise HTTPException(status_code=500, detail="Error fetching divorce cases")

@router.post("/scrape", response_model=List[DivorceCase])
async def scrape_cases():
    """
    Scrape new divorce cases and save them to the database
    """
    try:
        cases = await divorce_scraper_service.scrape_new_cases()
        return cases
    except Exception as e:
        logger.error(f"Error scraping divorce cases: {e}")
        raise HTTPException(status_code=500, detail="Error scraping divorce cases") 