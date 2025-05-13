from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.api.v1.api import api_router
from app.utils.montgomery_probate_case_scraper import MontgomeryProbateCaseScraper
from app.services.montgomery_probate_case_service import MontgomeryProbateCaseService
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

# Set up CORS middleware with appropriate origins
origins = ["*"] if settings.ALLOW_ALL_ORIGINS else [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]

# Note: When allow_origins=["*"], allow_credentials must be False according to CORS spec
allow_credentials = not settings.ALLOW_ALL_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],  # Allow all headers for maximum compatibility
    expose_headers=["Content-Type", "Set-Cookie", "Authorization"],
    max_age=600,  # Maximum time (in seconds) that results can be cached
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db(recreate=False)  # Set recreate=False to preserve existing tables

@app.get("/")
async def root():
    return {"message": "Welcome to the Probate Case Scraper API"}

@app.get("/cors-test")
async def cors_test():
    """Endpoint to test if CORS is working properly"""
    return {
        "message": "CORS is configured correctly!",
        "allow_all_origins": settings.ALLOW_ALL_ORIGINS,
        "cors_origins": origins
    }

@app.post("/scrape")
async def scrape_probate_cases():
    """Endpoint to trigger the probate case scraping process"""
    try:
        db = SessionLocal()
        scraper = MontgomeryProbateCaseScraper()
        service = MontgomeryProbateCaseService(db)
        
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