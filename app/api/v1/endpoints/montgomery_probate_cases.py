from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from loguru import logger

from app.core.database import get_db
from app.schemas.montgomery_probate_case import MontgomeryProbateCase
from app.services.montgomery_probate_case_service import MontgomeryProbateCaseService
from app.utils.montgomery_probate_case_scraper import MontgomeryProbateCaseScraper

router = APIRouter()

@router.get("/", response_model=List[MontgomeryProbateCase])
def get_probate_cases(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all probate cases"""
    service = MontgomeryProbateCaseService(db)
    return service.get_all_probate_cases()[skip:skip + limit]

@router.get("/{case_number}", response_model=MontgomeryProbateCase)
def get_probate_case(
    case_number: str,
    db: Session = Depends(get_db)
):
    """Get a specific probate case by case number"""
    service = MontgomeryProbateCaseService(db)
    case = service.get_probate_case(case_number)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.post("/scrape")
async def scrape_probate_cases(db: Session = Depends(get_db)):
    """Trigger the scraping process for probate cases"""
    try:
        logger.info("Starting probate case scraping process")
        
        # Initialize scraper and service
        scraper = MontgomeryProbateCaseScraper()
        service = MontgomeryProbateCaseService(db)
        
        # Get all cases
        logger.info("Fetching cases from website")
        cases = await scraper.scrape_all_cases()
        logger.info(f"Found {len(cases)} cases to process")
        
        saved_cases = []
        updated_cases = []
        skipped_cases = []
        
        # Process each case
        for case in cases:
            try:
                if not service.case_exists(case.case_number):
                    logger.info(f"Creating new case: {case.case_number}")
                    db_case = service.create_probate_case(case)
                    saved_cases.append(db_case)
                    logger.info(f"Successfully created case: {case.case_number}")
                else:
                    logger.info(f"Updating existing case: {case.case_number}")
                    db_case = service.update_probate_case(case)
                    updated_cases.append(db_case)
                    logger.info(f"Successfully updated case: {case.case_number}")
            except Exception as case_error:
                logger.error(f"Error processing case {case.case_number}: {str(case_error)}")
                logger.exception("Full traceback:")
                skipped_cases.append(case.case_number)
                continue
        
        # Log summary
        logger.info(f"Scraping completed. Added {len(saved_cases)} new cases, updated {len(updated_cases)} cases, skipped {len(skipped_cases)} cases")
        
        return {
            "message": "Scraping completed successfully",
            "new_cases_added": len(saved_cases),
            "cases_updated": len(updated_cases),
            "skipped_cases": len(skipped_cases),
            "total_cases_scraped": len(cases),
            "new_case_numbers": [case.case_number for case in saved_cases],
            "updated_case_numbers": [case.case_number for case in updated_cases],
            "skipped_case_numbers": skipped_cases
        }
    except Exception as e:
        logger.error(f"Error in scrape_probate_cases: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e)) 