from typing import List
from loguru import logger
from app.core.config import settings
from app.core.database import get_db
from app.schemas.montgomery_foreclosure_case import MontgomeryForeclosureCaseCreate
from app.utils.recaptcha import get_recaptcha_token
from app.utils.montgomery_foreclosure_scraper import scrape_case_ids, scrape_case_details, save_to_database

class MontgomeryForeclosureScraperService:
    async def scrape_new_cases(self) -> List[MontgomeryForeclosureCaseCreate]:
        """
        Scrape new foreclosure cases and save them to the database
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

            return case_details_list

        except Exception as e:
            logger.error(f"Error scraping foreclosure cases: {e}")
            raise 