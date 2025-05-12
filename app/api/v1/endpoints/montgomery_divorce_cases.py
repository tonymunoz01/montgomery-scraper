from typing import List
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.core.database import get_db
from app.services.montgomery_divorce_scraper import MontgomeryDivorceScraperService
from app.schemas.montgomery_divorce_case import MontgomeryDivorceCase, MontgomeryDivorceCaseCreate

router = APIRouter()
divorce_scraper_service = MontgomeryDivorceScraperService()

@router.get("/", response_model=List[MontgomeryDivorceCase])
async def get_cases(db=Depends(get_db)):
    """
    Get all divorce cases from the database
    """
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM montgomery_divorce_cases ORDER BY created_at DESC")
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching divorce cases: {e}")
        raise HTTPException(status_code=500, detail="Error fetching divorce cases")

@router.post("/scrape", response_model=List[MontgomeryDivorceCase])
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