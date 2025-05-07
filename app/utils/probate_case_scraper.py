import aiohttp
import asyncio
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
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = settings.PROBATE_CASE_SEARCH_URL

class ProbateCaseScraper:
    def __init__(self):
        self.session = None
        self.db = SessionLocal()
    
    def __del__(self):
        """Close database session when scraper is destroyed"""
        if self.db:
            self.db.close()
    
    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def get_full_url(self, relative_url: str) -> str:
        """Convert relative URL to full URL"""
        if relative_url.startswith('http'):
            return relative_url
        # Remove any leading slash
        relative_url = relative_url.lstrip('/')
        return urljoin(BASE_URL, relative_url)
    
    async def get_case_list(self) -> List[str]:
        """Get a list of case URLs from the search page"""
        try:
            await self.init_session()
            
            # First get the search page to get cookies
            logger.info("Getting initial search page...")
            async with self.session.get(BASE_URL) as response:
                response.raise_for_status()
            
            # Prepare form data
            form_data = {
                'SEARCH': 'go', 
                'caseyear': '2025'
            }
            
            logger.info(f"Submitting search form with data: {form_data}")
            async with self.session.post(BASE_URL, data=form_data) as response:
                response.raise_for_status()
                html = await response.text()
            
            soup = BeautifulSoup(html, 'html.parser')
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
            return {}
    
    async def get_case_details(self, case_url: str) -> Dict:
        """Get detailed information for a specific case"""
        try:
            logger.info(f"Fetching details for case at URL: {case_url}")
            
            async with self.session.get(case_url) as response:
                response.raise_for_status()
                html = await response.text()
            
            soup = BeautifulSoup(html, 'html.parser')
            details = {
                'decedent_name': '',
                'filing_date': '',
                'case_number': '',
                'source_url': case_url,
                'county': 'Montgomery County, Ohio',
                'case_status': '',
                'property_address': '',
                'fiduciary_name': '',
                'fiduciary_address': '',
                'fiduciary_city': '',
                'fiduciary_zip': ''
            }
            
            # Find all tables in the page
            tables = soup.find_all('table')
            if not tables:
                logger.warning("Could not find any tables in the page")
                return {}
            
            # Process each table to find relevant information
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                    
                    label = cells[0].get_text(strip=True).lower()
                    value_cell = cells[1]
                    
                    # Extract decedent name
                    if "decedent's name" in label:
                        details['decedent_name'] = value_cell.get_text(strip=True)
                        logger.info(f"Found decedent name: {details['decedent_name']}")
                    
                    # Extract case number
                    elif "case number" in label:
                        details['case_number'] = value_cell.get_text(strip=True)
                        logger.info(f"Found case number: {details['case_number']}")
                    
                    # Extract case status and filing date
                    elif "case status" in label:
                        value = value_cell.get_text(strip=True)
                        logger.info(f"Raw case status value: {value}")
                        
                        # Split by space to separate status and date
                        parts = value.split()
                        if len(parts) >= 2:
                            status = parts[0].strip()
                            date_str = ' '.join(parts[1:]).strip()
                            
                            # Store the status regardless of whether it's OPEN or REOPEN
                            details['case_status'] = status
                            logger.info(f"Found case status: {status}")
                            
                            try:
                                date_obj = datetime.strptime(date_str, '%m-%d-%Y')
                                details['filing_date'] = date_obj.strftime('%Y-%m-%d')
                                logger.info(f"Found filing date: {date_str}")
                            except ValueError as e:
                                logger.warning(f"Could not parse filing date from: {date_str}")
                        else:
                            logger.warning(f"Invalid case status format: {value}")
                            # Still store the status even if we can't parse the date
                            details['case_status'] = value.strip()
                            logger.info(f"Stored raw case status: {value.strip()}")
                    
                    # Extract property address
                    elif "property address" in label:
                        details['property_address'] = value_cell.get_text(strip=True)
                        logger.info(f"Found property address: {details['property_address']}")
                    
                    # Extract fiduciary information
                    elif "fiduciary" in label:
                        # Get the raw HTML content of the cell
                        fiduciary_html = str(value_cell)
                        logger.info(f"Raw fiduciary HTML: {fiduciary_html}")
                        
                        # Extract name (first line before <br>)
                        name_match = re.search(r'>\s*([^<]+?)\s*<br', fiduciary_html)
                        if name_match:
                            details['fiduciary_name'] = name_match.group(1).strip()
                            logger.info(f"Found fiduciary name: {details['fiduciary_name']}")
                        
                        # Extract address using BeautifulSoup
                        br_tag = value_cell.find('br')
                        if br_tag:
                            # Get all text after the <br> tag
                            address_text = br_tag.next_sibling
                            if address_text:
                                full_address = address_text.strip()
                                # Clean up any extra whitespace or newlines
                                full_address = ' '.join(full_address.split())
                                logger.info(f"Found raw address: {full_address}")
                                
                                # Split on first comma to separate street address from city/state/zip
                                address_parts = full_address.split(',', 1)
                                if len(address_parts) >= 2:
                                    # First part is the street address
                                    details['fiduciary_address'] = address_parts[0].strip()
                                    
                                    # Second part contains city, state, and zip
                                    city_state_zip = address_parts[1].strip()
                                    
                                    # Split by spaces and handle state and zip
                                    parts = city_state_zip.split()
                                    if len(parts) >= 2:
                                        # Find the index of the state (OH)
                                        state_index = -1
                                        for i, part in enumerate(parts):
                                            if part == 'OH':
                                                state_index = i
                                                break
                                        
                                        if state_index != -1:
                                            # Everything before the state is the city
                                            details['fiduciary_city'] = parts[state_index - 1].strip()
                                            # Zip is the last part
                                            details['fiduciary_zip'] = parts[-1].strip()
                                        else:
                                            # If we can't find the state, try to parse based on position
                                            if len(parts) >= 3:  # We expect at least city, state, zip
                                                # Assume last part is zip, second to last is state, rest is city
                                                details['fiduciary_city'] = parts[-3].strip()
                                                details['fiduciary_zip'] = parts[-1].strip()
                                            else:
                                                # If we can't parse it properly, store the full address
                                                details['fiduciary_address'] = full_address
                                                logger.warning(f"Could not parse address components from: {full_address}")
                                    else:
                                        # If we can't parse it properly, store the full address
                                        details['fiduciary_address'] = full_address
                                        logger.warning(f"Could not parse address components from: {full_address}")
                                else:
                                    # If we can't parse it properly, store the full address
                                    details['fiduciary_address'] = full_address
                                    logger.warning(f"Could not parse address components from: {full_address}")
                                
                                logger.info(f"Parsed address components:")
                                logger.info(f"  Street: {details['fiduciary_address']}")
                                logger.info(f"  City: {details['fiduciary_city']}")
                                logger.info(f"  Zip: {details['fiduciary_zip']}")
                        else:
                            logger.warning(f"Could not find <br> tag in fiduciary HTML")
            
            # Check if we found all required fields
            missing_fields = [field for field, value in details.items() if not value and field not in ['county', 'case_status', 'property_address', 'fiduciary_name', 'fiduciary_address', 'fiduciary_city', 'fiduciary_zip']]
            if missing_fields:
                logger.warning(f"Missing required fields: {missing_fields}")
                return {}
            
            logger.info(f"Successfully extracted details for case: {details['case_number']}")
            return details
            
        except Exception as e:
            logger.error(f"Error getting case details for {case_url}: {str(e)}")
            logger.exception("Full traceback:")
            return {}
    
    async def save_case_to_db(self, case_details: Dict) -> None:
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
                county=case_details['county'],
                fiduciary_name=case_details.get('fiduciary_name'),
                fiduciary_address=case_details.get('fiduciary_address'),
                fiduciary_city=case_details.get('fiduciary_city'),
                fiduciary_zip=case_details.get('fiduciary_zip')
            )
            
            self.db.add(new_case)
            self.db.commit()
            logger.info(f"Saved OPEN/REOPEN case {case_details['case_number']} to database")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving case to database: {str(e)}")
            logger.exception("Full traceback:")

    async def scrape_all_case_details(self) -> None:
        """Scrape details for all OPEN and REOPEN cases and save to database"""
        try:
            # Get case URLs from search results
            urls = await self.get_case_list()
            logger.info(f"Processing {len(urls)} URLs for OPEN and REOPEN cases")
            
            # Process cases in batches to avoid overwhelming the server
            batch_size = 5
            for i in range(0, len(urls), batch_size):
                batch = urls[i:i + batch_size]
                tasks = []
                for url in batch:
                    tasks.append(self.get_case_details(url))
                
                # Wait for all tasks in the batch to complete
                results = await asyncio.gather(*tasks)
                
                # Save results to database
                for details in results:
                    if details:
                        await self.save_case_to_db(details)
                
                # Add a small delay between batches
                await asyncio.sleep(1)
            
            logger.info("Scraping completed")
            
        except Exception as e:
            logger.error(f"Error in scrape_all_case_details: {str(e)}")
            logger.exception("Full traceback:")
        finally:
            await self.close_session()
    
    async def scrape_all_cases(self) -> List[ProbateCaseCreate]:
        """Scrape all available cases that are OPEN or REOPEN"""
        logger.info("Starting scraping process for OPEN and REOPEN cases")
        cases = []
        case_list = await self.get_case_list()
        logger.info(f"Retrieved {len(case_list)} cases from search page")
        
        # Process cases in batches
        batch_size = 5
        for i in range(0, len(case_list), batch_size):
            batch = case_list[i:i + batch_size]
            tasks = []
            for case in batch:
                tasks.append(self.get_case_details(case))
            
            # Wait for all tasks in the batch to complete
            results = await asyncio.gather(*tasks)
            
            # Process results
            for details in results:
                if details:
                    try:
                        probate_case = ProbateCaseCreate(**details)
                        cases.append(probate_case)
                        logger.info(f"Successfully created ProbateCase object: {probate_case}")
                    except Exception as e:
                        logger.error(f"Error creating probate case from details: {str(e)}")
                        logger.error(f"Problem details: {details}")
                        logger.exception("Full traceback:")
            
            # Add a small delay between batches
            await asyncio.sleep(1)
        
        logger.info(f"Scraping completed. Found {len(cases)} OPEN/REOPEN cases out of {len(case_list)} total cases")
        await self.close_session()
        return cases 