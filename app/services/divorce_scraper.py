from typing import List
from loguru import logger
from app.core.config import settings
from app.core.database import get_db
from app.models.divorce_case import DivorceCase
from app.schemas.divorce_case import DivorceCase as DivorceCaseSchema
from app.utils.recaptcha import get_recaptcha_token
from app.utils.divorce_scraper import scrape_case_ids, scrape_case_details, save_to_database

class DivorceScraperService:
    async def scrape_new_cases(self) -> List[DivorceCaseSchema]:
        """
        Scrape new divorce cases and save them to the database
        """
        try:
            # Get recaptcha token
            captcha_token = get_recaptcha_token()
            if not captcha_token:
                logger.error("Failed to get recaptcha token")
                return []

            # Scrape case IDs
            case_ids = scrape_case_ids(captcha_token)
            logger.info(f"Found {len(case_ids)} cases to process")

            # Process each case ID and collect details
            case_details_list = []
            for case_id in case_ids:
                logger.info(f"Processing case ID: {case_id}")
                case_details = scrape_case_details(case_id)
                if case_details:
                    case_details_list.append(case_details)

            # Save to PostgreSQL database
            save_to_database(case_details_list)
            logger.info(f"Successfully saved {len(case_details_list)} case details to PostgreSQL database")

            # Get the saved cases from the database to return with proper id and created_at
            db = next(get_db())
            saved_cases = db.query(DivorceCase).filter(
                DivorceCase.case_id.in_([case['case_id'] for case in case_details_list])
            ).all()
            db.close()

            # Convert SQLAlchemy models to Pydantic schemas
            return [DivorceCaseSchema.from_orm(case) for case in saved_cases]

        except Exception as e:
            logger.error(f"Error scraping divorce cases: {e}")
            raise 