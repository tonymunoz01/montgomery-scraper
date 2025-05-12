from typing import List
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.core.database import get_db
from app.services.montgomery_foreclosure_scraper import MontgomeryForeclosureScraperService
from app.schemas.montgomery_foreclosure_case import MontgomeryForeclosureCase, MontgomeryForeclosureCaseCreate

router = APIRouter()
foreclosure_scraper_service = MontgomeryForeclosureScraperService()

@router.get("/", response_model=List[MontgomeryForeclosureCase], operation_id="get_foreclosure_cases")
async def get_cases(db=Depends(get_db)):
    """
    Get all foreclosure cases from the database
    """
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM montgomery_foreclosure_cases ORDER BY created_at DESC")
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching foreclosure cases: {e}")
        raise HTTPException(status_code=500, detail="Error fetching foreclosure cases")

@router.post("/scrape", response_model=List[MontgomeryForeclosureCase], operation_id="scrape_foreclosure_cases")
async def scrape_cases():
    """
    Scrape new foreclosure cases and save them to the database
    """
    try:
        cases = await foreclosure_scraper_service.scrape_new_cases()
        return cases
    except Exception as e:
        logger.error(f"Error scraping foreclosure cases: {e}")
        raise HTTPException(status_code=500, detail="Error scraping foreclosure cases")

@router.get("/{case_id}", response_model=MontgomeryForeclosureCase, operation_id="get_foreclosure_case_by_id")
async def get_case(case_id: str, db=Depends(get_db)):
    """
    Get a specific foreclosure case by ID
    """
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM montgomery_foreclosure_cases WHERE case_id = %s", (case_id,))
            case = cur.fetchone()
            if not case:
                raise HTTPException(status_code=404, detail="Foreclosure case not found")
            return case
    except Exception as e:
        logger.error(f"Error fetching foreclosure case {case_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching foreclosure case") 