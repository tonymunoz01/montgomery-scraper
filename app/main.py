from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.api.v1.api import api_router
from app.services.probate_case_scraper import ProbateCaseScraper
from app.services.probate_case_service import ProbateCaseService
from app.core.database import SessionLocal, init_db

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/app.log", rotation="500 MB")

app = FastAPI(
    title="Scraping API",
    description="API for scraping and managing probate case data from Montgomery County, Ohio court website",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db(recreate=True)  # Set recreate=True to drop and recreate tables

@app.get("/")
async def root():
    return {"message": "Welcome to the Probate Case Scraper API"}

@app.post("/scrape")
async def scrape_probate_cases():
    """Endpoint to trigger the probate case scraping process"""
    try:
        db = SessionLocal()
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
        logger.error(f"Error during scraping: {str(e)}")
        return {"error": str(e)}
    finally:
        db.close() 