from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.probate_case import ProbateCase
from app.services.probate_case_service import ProbateCaseService
from app.utils.probate_case_scraper import ProbateCaseScraper

router = APIRouter()

@router.get("/", response_model=List[ProbateCase])
def get_probate_cases(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all probate cases"""
    service = ProbateCaseService(db)
    return service.get_all_probate_cases()[skip:skip + limit]

@router.get("/{case_number}", response_model=ProbateCase)
def get_probate_case(
    case_number: str,
    db: Session = Depends(get_db)
):
    """Get a specific probate case by case number"""
    service = ProbateCaseService(db)
    case = service.get_probate_case(case_number)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.post("/scrape")
def scrape_probate_cases(db: Session = Depends(get_db)):
    """Trigger the scraping process for probate cases"""
    try:
        scraper = ProbateCaseScraper()
        service = ProbateCaseService(db)
        
        cases = scraper.scrape_all_cases()
        new_cases = []
        
        for case in cases:
            if not service.case_exists(case.case_number):
                db_case = service.create_probate_case(case)
                new_cases.append(db_case)
        
        return {
            "message": "Scraping completed successfully",
            "new_cases_added": len(new_cases),
            "total_cases_scraped": len(cases)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 