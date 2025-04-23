import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import logging
import urllib.parse
from app.schemas.probate_case import ProbateCaseCreate
import json
import os
from urllib.parse import urljoin
import time
from sqlalchemy.orm import Session
from app.models.probate_case import ProbateCase
from app.core.database import SessionLocal
import uuid
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = settings.PROBATE_CASE_SEARCH_URL

class ProbateCaseScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.db = SessionLocal()
    
    def __del__(self):
        """Close database session when scraper is destroyed"""
        self.db.close()
    
    def get_full_url(self, relative_url: str) -> str:
        """Convert relative URL to full URL"""
        if relative_url.startswith('http'):
            return relative_url
        # Remove any leading slash
        relative_url = relative_url.lstrip('/')
        return urljoin(BASE_URL, relative_url)
    
    def get_case_list(self) -> List[str]:
        """Get a list of case URLs from the search page"""
        try:
            # First get the search page to get cookies
            logger.info("Getting initial search page...")
            response = self.session.get(BASE_URL)
            response.raise_for_status()
            
            # Prepare form data
            form_data = {
                'search': 'go'
            }
            
            logger.info(f"Submitting search form with data: {form_data}")
            response = self.session.post(BASE_URL, data=form_data)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            case_urls = []
            
            # Find all links in tables
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and 'casesearchresultx.cfm' in href:
                    # Convert relative URL to absolute URL
                    absolute_url = self.get_full_url(href)
                    case_urls.append(absolute_url)
            
            # Remove duplicates while preserving order
            case_urls = list(dict.fromkeys(case_urls))
            
            logger.info(f"Found {len(case_urls)} case URLs")
            return case_urls
            
        except Exception as e:
            logger.error(f"Error getting case list: {str(e)}")
            logger.exception("Full traceback:")
            return []
    
    def save_case_to_db(self, case_details: Dict) -> None:
        """Save case details to the database"""
        try:
            # Double check case status is OPEN or REOPEN
            if case_details.get('case_status') not in ["OPEN", "REOPEN"]:
                logger.info(f"Skipping case {case_details.get('case_number')} with status: {case_details.get('case_status')}")
                return
            
            # Check if case already exists
            existing_case = self.db.query(ProbateCase).filter(
                ProbateCase.case_number == case_details['case_number']
            ).first()
            
            if existing_case:
                logger.info(f"Case {case_details['case_number']} already exists in database")
                return
            
            # Create new case
            new_case = ProbateCase(
                id=str(uuid.uuid4()),
                decedent_name=case_details['decedent_name'],
                filing_date=datetime.strptime(case_details['filing_date'], '%Y-%m-%d').date(),
                case_number=case_details['case_number'],
                source_url=case_details['source_url'],
                county=case_details['county']
            )
            
            self.db.add(new_case)
            self.db.commit()
            logger.info(f"Saved OPEN/REOPEN case {case_details['case_number']} to database")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving case to database: {str(e)}")
            logger.exception("Full traceback:")

    def get_case_details(self, case_url: str) -> Dict:
        """Get detailed information for a specific case"""
        try:
            logger.info(f"Fetching details for case at URL: {case_url}")
            
            response = self.session.get(case_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            details = {
                'decedent_name': '',
                'filing_date': None,
                'case_number': '',
                'source_url': case_url,
                'county': 'Montgomery County, Ohio',
                'case_status': ''
            }
            
            # Find the main details table
            tables = soup.find_all('table', {'width': '95%'})
            if not tables:
                logger.warning("Could not find details table")
                return {}
            
            main_table = tables[0]
            rows = main_table.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                
                # Extract decedent name
                if "decedent's name" in label:
                    details['decedent_name'] = value.strip()
                    logger.info(f"Found decedent name: {value.strip()}")
                
                # Extract case number
                elif "case number" in label:
                    details['case_number'] = value.strip()
                    logger.info(f"Found case number: {value.strip()}")
                
                # Extract case status and filing date
                elif "case status" in label:
                    # Split the value into status and date parts
                    parts = value.strip().split()
                    if len(parts) >= 2:
                        status = parts[0].strip()
                        date_str = ' '.join(parts[1:]).strip()
                        
                        # Only process if status is OPEN or REOPEN
                        if status not in ["OPEN", "REOPEN"]:
                            logger.info(f"Skipping case {details['case_number']} with status: {status}")
                            return {}
                        
                        details['case_status'] = status
                        logger.info(f"Found case status: {status}")
                        
                        try:
                            # Convert from MM-DD-YYYY to YYYY-MM-DD format
                            date_obj = datetime.strptime(date_str, '%m-%d-%Y')
                            details['filing_date'] = date_obj.strftime('%Y-%m-%d')
                            logger.info(f"Found filing date: {date_str}")
                        except ValueError as e:
                            logger.warning(f"Could not parse filing date from: {date_str}")
                    else:
                        logger.warning(f"Invalid case status format: {value}")
                        return {}
            
            # Check if we found all required fields
            missing_fields = [field for field, value in details.items() if not value and field not in ['county', 'case_status']]
            if missing_fields:
                logger.warning(f"Missing required fields: {missing_fields}")
                return {}
            
            logger.info(f"Successfully extracted details for case: {details['case_number']}")
            return details
            
        except Exception as e:
            logger.error(f"Error getting case details for {case_url}: {str(e)}")
            logger.exception("Full traceback:")
            return {}

    def scrape_all_case_details(self) -> None:
        """Scrape details for all OPEN and REOPEN cases and save to database"""
        try:
            # Get case URLs from search results
            urls = self.get_case_list()
            logger.info(f"Processing {len(urls)} URLs for OPEN and REOPEN cases")
            
            open_reopen_count = 0
            for i, url in enumerate(urls, 1):
                try:
                    logger.info(f"Processing case {i} of {len(urls)}")
                    details = self.get_case_details(url)
                    if details:
                        self.save_case_to_db(details)
                        if details.get('case_status') in ["OPEN", "REOPEN"]:
                            open_reopen_count += 1
                    
                    # Add a small delay between requests to avoid overwhelming the server
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {str(e)}")
                    logger.exception("Full traceback:")
                    continue
            
            logger.info(f"Scraping completed. Found {open_reopen_count} OPEN/REOPEN cases out of {len(urls)} total cases")
            
        except Exception as e:
            logger.error(f"Error in scrape_all_case_details: {str(e)}")
            logger.exception("Full traceback:")
    
    def scrape_all_cases(self) -> List[ProbateCaseCreate]:
        """Scrape all available cases that are OPEN or REOPEN"""
        logger.info("Starting scraping process for OPEN and REOPEN cases")
        cases = []
        case_list = self.get_case_list()
        logger.info(f"Retrieved {len(case_list)} cases from search page")
        
        for i, case in enumerate(case_list, 1):
            logger.info(f"Processing case {i} of {len(case_list)}: {case}")
            details = self.get_case_details(case)
            if details:
                try:
                    probate_case = ProbateCaseCreate(**details)
                    cases.append(probate_case)
                    logger.info(f"Successfully created ProbateCase object: {probate_case}")
                except Exception as e:
                    logger.error(f"Error creating probate case from details: {str(e)}")
                    logger.error(f"Problem details: {details}")
                    logger.exception("Full traceback:")
        
        logger.info(f"Scraping completed. Found {len(cases)} OPEN/REOPEN cases out of {len(case_list)} total cases")
        return cases 