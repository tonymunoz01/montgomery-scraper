import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict
import re
import os
from dotenv import load_dotenv
from loguru import logger
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.models.divorce_case import DivorceCase
from app.utils.recaptcha import get_recaptcha_token

def get_search_results(captcha_token: str) -> str:
    """
    Make a request to the backend with the recaptcha token and get the HTML response.
    """
    try:
        logger.info("Starting search request process...")
        logger.info(f"Received reCAPTCHA token: {captcha_token[:20]}...")
        
        session = requests.Session()
        logger.info("Created new session")
        
        # Get URLs from settings
        general_search_results_url = settings.GENERAL_SEARCH_RESULTS_URL
        base_url = settings.PAGE_URL.rstrip('/')
        
        # Updated headers to match what a browser would send
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': base_url,
            'Referer': base_url,
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
        }
        
        # First get the initial page to get VIEWSTATE and EVENTVALIDATION
        logger.info(f"Fetching initial page from {base_url}")
        initial_response = session.get(base_url)
        initial_response.raise_for_status()
        logger.info("Successfully retrieved initial page")
        
        soup = BeautifulSoup(initial_response.text, 'html.parser')
        
        # Extract VIEWSTATE and EVENTVALIDATION
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})
        
        # Prepare form data
        data = {
            '__VIEWSTATE': viewstate['value'] if viewstate else '',
            '__EVENTVALIDATION': eventvalidation['value'] if eventvalidation else '',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            'searchType': 'general',
            'captchaToken': captcha_token,
            'ctl00$ContentPlaceHolder1$txtCaseNumber': '',
            'ctl00$ContentPlaceHolder1$txtPartyName': '',
            'ctl00$ContentPlaceHolder1$txtAttorneyName': '',
            'ctl00$ContentPlaceHolder1$txtAttorneyBarNumber': '',
            'ctl00$ContentPlaceHolder1$txtCaseType': 'DIVORCE WITH CHILDREN (DRC)',
            'ctl00$ContentPlaceHolder1$txtCaseStatus': 'OPEN',
            'ctl00$ContentPlaceHolder1$txtFilingDateFrom': '',
            'ctl00$ContentPlaceHolder1$txtFilingDateTo': '',
            'ctl00$ContentPlaceHolder1$btnSearch': 'Search'
        }
        
        logger.info("Sending search request with the following parameters:")
        logger.info(f"Search Type: {data['searchType']}")
        logger.info(f"Case Type: {data['ctl00$ContentPlaceHolder1$txtCaseType']}")
        logger.info(f"Case Status: {data['ctl00$ContentPlaceHolder1$txtCaseStatus']}")
        
        # Make the actual request
        logger.info(f"Making request to: {general_search_results_url}")
        response = session.post(general_search_results_url, headers=headers, data=data)
        response.raise_for_status()
        
        # Print response details for debugging
        logger.info(f"Response Status Code: {response.status_code}")
        logger.info(f"Response Headers: {response.headers}")
        logger.info(f"Response Content Length: {len(response.text)}")
        
        return response.text
        
    except Exception as e:
        logger.error(f"Error getting search results: {e}")
        if 'response' in locals():
            logger.error(f"Response Status Code: {response.status_code}")
            logger.error(f"Response Headers: {response.headers}")
            logger.error(f"Response Content: {response.text[:1000]}")
        return None

def scrape_case_ids(captcha_token: str) -> List[Dict]:
    """
    Scrape case IDs from the HTML response where the case type is DIVORCE WITH CHILDREN (DRC)
    and directly scrape case details for each case.
    """
    try:
        logger.info("Starting case ID scraping process...")
        
        html_content = get_search_results(captcha_token)
        if not html_content:
            logger.error("Failed to get HTML content")
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the table body with id 'tblSearchResults'
        table_body = soup.find('tbody', {'id': 'tblSearchResults'})
        if not table_body:
            logger.error("Could not find table body with id 'tblSearchResults'")
            # Log a sample of the HTML to help debug
            logger.error("HTML sample:")
            logger.error(html_content[:2000])  # First 2000 characters
            return []
            
        rows = table_body.find_all('tr')
        logger.info(f"Found {len(rows)} total rows in the table")
        
        case_details_list = []
        
        for row in rows:
            # Get the case type from the second column
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
                
            case_type = cells[1].text.strip()
            if case_type != 'DIVORCE WITH CHILDREN (DRC)':
                continue
                
            # Get the onclick attribute
            onclick_attr = row.get('onclick', '')
            if not onclick_attr:
                continue
                
            # Extract case ID and case number using regex
            # Pattern to match: openTab('caseInfo','case_id=1321747&screen=summary',1,'2012 DR 00416')
            case_id_match = re.search(r"case_id=(\d+)", onclick_attr)
            case_number_match = re.search(r"'\d{4}\s+DR\s+\d{5}'", onclick_attr)
            
            if case_id_match and case_number_match:
                case_id = case_id_match.group(1)
                case_number = case_number_match.group(0).strip("'")
                case_data = {
                    'case_id': case_id,
                    'case_number': case_number
                }
                logger.info(f"Found DRC case ID: {case_id} with case number: {case_number}")
                
                # Directly scrape case details
                case_details = scrape_case_details(case_data)
                if case_details:
                    case_details_list.append(case_details)
                    logger.info(f"Successfully scraped details for case ID: {case_id}")
                else:
                    logger.error(f"Failed to scrape details for case ID: {case_id}")
            else:
                logger.warning(f"Could not extract case_id or case_number from: {onclick_attr}")
        
        logger.info(f"Scraping complete. Found and processed {len(case_details_list)} DRC cases")
        return case_details_list
    
    except Exception as e:
        logger.error(f"Error scraping case IDs: {str(e)}")
        return []

def scrape_case_details(case_data: Dict) -> Dict:
    """
    Scrape case details for a given case.
    """
    case_info_url = f"{settings.PAGE_URL}/Helpers/caseInformation.aspx"
    
    logger.info(f"Starting to scrape details for case ID: {case_data['case_id']}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': settings.PAGE_URL,
        'Referer': settings.PAGE_URL,
    }
    
    try:
        session = requests.Session()
        data = {
            'case_id': case_data['case_id'],
            'screen': 'summary'
        }
        
        logger.info(f"Making request for case details to {case_info_url}")
        response = session.post(case_info_url, headers=headers, data=data)
        response.raise_for_status()
        logger.info(f"Successfully retrieved case details for case ID: {case_data['case_id']}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize the case details dictionary with required fields
        case_details = {
            'id': None,  # Will be set by the database
            'case_id': case_data['case_id'],
            'case_number': case_data['case_number'],
            'filing_date': '',
            'status': '',
            'plaintiff': '',
            'defendant': '',
            'county': 'Montgomery',
            'created_at': None  # Will be set by the database
        }
        
        # Find all table cells that might contain our data
        cells = soup.find_all(['td', 'th'])
        
        for i, cell in enumerate(cells):
            cell_text = cell.text.strip()
            
            # Look for labels and their corresponding values
            if 'File Date:' in cell_text:
                next_cell = cells[i + 1] if i + 1 < len(cells) else None
                if next_cell:
                    case_details['filing_date'] = next_cell.text.strip()
            
            elif 'Status:' in cell_text:
                next_cell = cells[i + 1] if i + 1 < len(cells) else None
                if next_cell:
                    case_details['status'] = next_cell.text.strip()
        
        # Special handling for plaintiff and defendant information
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                first_cell_text = cells[0].text.strip().upper()
                
                # Handle PLAINTIFF
                if first_cell_text.strip() == 'PLAINTIFF':
                    case_details['plaintiff'] = cells[1].text.strip()
                
                # Handle DEFENDANT
                elif 'DEFENDANT' in first_cell_text:
                    defendant_text = cells[1].text.strip()
                    if defendant_text:
                        case_details['defendant'] = defendant_text
        
        # Log the case details for debugging
        logger.info(f"Successfully scraped case ID {case_data['case_id']}:")
        logger.info(json.dumps(case_details, indent=2))
        
        return case_details
        
    except Exception as e:
        logger.error(f"Error scraping case details for case ID {case_data['case_id']}: {e}")
        if 'response' in locals():
            logger.error(f"Response content: {response.text[:1000]}")
        else:
            logger.error("No response available")
        return None

def save_to_database(data: List[Dict[str, str]]) -> None:
    """
    Save the scraped data to the database.
    """
    try:
        logger.info("Starting to save data to database")
        db = next(get_db())
        
        logger.info("Ensuring divorce_cases table exists")
        DivorceCase.__table__.create(db.get_bind(), checkfirst=True)
        logger.info("Divorce_cases table exists or was created successfully")
        
        new_cases_added = 0
        
        for case in data:
            if not case:
                continue
                
            existing_case = db.query(DivorceCase).filter(
                DivorceCase.case_id == case['case_id']
            ).first()
            
            if not existing_case:
                new_case = DivorceCase(**case)
                db.add(new_case)
                new_cases_added += 1
                logger.info(f"Successfully saved case {case['case_id']} to database")
            else:
                logger.info(f"Case ID {case['case_id']} already exists in database, skipping...")
        
        db.commit()
        logger.info(f"Successfully saved {new_cases_added} new cases to database")
        
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
        if 'db' in locals():
            db.rollback()
        raise
    finally:
        if 'db' in locals():
            db.close()

def run_scraper() -> None:
    """
    Run the divorce case scraper.
    """
    try:
        logger.info("Starting divorce case scraper")
        
        captcha_token = get_recaptcha_token()
        if not captcha_token:
            logger.error("Failed to get reCAPTCHA token")
            return
            
        # Log the full captcha token
        logger.info("Successfully obtained reCAPTCHA token:")
        logger.info(f"Token: {captcha_token}")
        logger.info(f"Token length: {len(captcha_token)}")
        
        case_details_list = scrape_case_ids(captcha_token)
        logger.info(f"Found {len(case_details_list)} cases to process")
        
        logger.info("Starting to save cases to database")
        save_to_database(case_details_list)
        logger.info("Scraping process completed successfully")
        
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")
        raise 