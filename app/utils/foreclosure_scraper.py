import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict
import re
from loguru import logger
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.models.foreclosure_case import ForeclosureCase
from app.utils.recaptcha import get_recaptcha_token

def get_search_results(captcha_token: str) -> str:
    """
    Make a request to the backend with the recaptcha token and get the HTML response.
    """
    try:
        logger.info("Starting search request process...")
        logger.info(f"Received reCAPTCHA token: {captcha_token[:20]}...")  # Log first 20 chars of token
        
        # Create a session to maintain cookies
        session = requests.Session()
        logger.info("Created new session")
        
        # First get the initial page
        logger.info(f"Fetching initial page from {settings.PAGE_URL}")
        initial_response = session.get(settings.PAGE_URL)
        initial_response.raise_for_status()
        logger.info("Successfully retrieved initial page")
        logger.info(f"Initial page status code: {initial_response.status_code}")
        logger.info(f"Initial page content length: {len(initial_response.text)} bytes")
        
        # Parse the initial page for ASP.NET form fields
        soup = BeautifulSoup(initial_response.text, 'html.parser')
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})
        
        logger.info("Preparing search request with reCAPTCHA token")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': settings.PAGE_URL.rstrip('/'),
            'Referer': settings.PAGE_URL,
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
        }
        
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
            'ctl00$ContentPlaceHolder1$txtCaseType': 'MORTGAGE FORECLOSURE (MF)',
            'ctl00$ContentPlaceHolder1$txtCaseStatus': 'OPEN',
            'ctl00$ContentPlaceHolder1$txtFilingDateFrom': '',
            'ctl00$ContentPlaceHolder1$txtFilingDateTo': '',
            'ctl00$ContentPlaceHolder1$btnSearch': 'Search'
        }
        
        logger.info("Sending search request with the following parameters:")
        logger.info(f"Case Type: {data['ctl00$ContentPlaceHolder1$txtCaseType']}")
        logger.info(f"Case Status: {data['ctl00$ContentPlaceHolder1$txtCaseStatus']}")
        logger.info(f"Search URL: {settings.GENERAL_SEARCH_RESULTS_URL}")
        logger.info(f"Request headers: {json.dumps(headers, indent=2)}")
        logger.info(f"Request data: {json.dumps(data, indent=2)}")
        
        # Make the search request
        logger.info(f"Making POST request to {settings.GENERAL_SEARCH_RESULTS_URL}")
        response = session.post(settings.GENERAL_SEARCH_RESULTS_URL, headers=headers, data=data)
        response.raise_for_status()
        
        logger.info(f"Search request completed with status code: {response.status_code}")
        logger.info(f"Response headers: {json.dumps(dict(response.headers), indent=2)}")
        logger.info(f"Response content length: {len(response.text)} bytes")
        
        # Print the response for debugging
        print("\n=== Response Content ===")
        print(response.text)
        print("=== End Response Content ===\n")
        
        # Check if we got a table in the response
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        if table:
            logger.info("Successfully retrieved HTML table with search results")
            rows = table.find_all('tr')
            logger.info(f"Found {len(rows)} rows in the results table")
            # Log the first row's content for debugging
            if rows:
                logger.info(f"First row content: {rows[0].text.strip()}")
        else:
            logger.warning("No table found in the response")
            logger.debug(f"Response content preview: {response.text[:500]}")
        
        return response.text
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request: {e}")
        if hasattr(e, 'response'):
            logger.error(f"Response Status Code: {e.response.status_code}")
            logger.error(f"Response Headers: {e.response.headers}")
            logger.error(f"Response Content: {e.response.text[:1000]}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error in get_search_results: {str(e)}")
        return ""

def scrape_case_ids(captcha_token: str) -> List[str]:
    """
    Scrape case IDs from the HTML response where the row contains both MORTGAGE FORECLOSURE (MF)
    and OPEN status with text-success class. Extracts case_id from onclick attribute.
    """
    try:
        logger.info("Starting case ID scraping process...")
        
        # Get HTML content from backend
        logger.info("Getting search results")
        html_content = get_search_results(captcha_token)
        if not html_content:
            logger.error("Failed to get HTML content")
            return []
        
        # Parse the HTML content
        logger.info("Parsing HTML content for case IDs")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all table rows
        rows = soup.find_all('tr')
        logger.info(f"Found {len(rows)} total rows in the table")
        
        # List to store matching case IDs
        case_data = []
        
        for row in rows:
            # Check if the row contains both required elements
            mf_cell = row.find('td', string='MORTGAGE FORECLOSURE (MF)')
            open_cell = row.find('td', class_='text-success', string='OPEN')
            reopen_cell = row.find('td', string='REOPENED')
            
            if mf_cell and (open_cell or reopen_cell):
                # Extract case_id from onclick attribute
                onclick_attr = row.get('onclick', '')
                # Look for case_id in the onclick attribute
                case_id_match = re.search(r'case_id\s*=\s*(\d+)', onclick_attr)
                
                if case_id_match:
                    case_id = case_id_match.group(1)
                    case_data.append(case_id)
                    logger.info(f"Found foreclosure case ID: {case_id}")
                    logger.info(f"Case Status: {'OPEN' if open_cell else 'REOPENED'}")
                else:
                    logger.warning(f"Found matching row but could not extract case_id from: {onclick_attr}")
        
        logger.info(f"Scraping complete. Found {len(case_data)} foreclosure case IDs")
        return case_data
    
    except Exception as e:
        logger.error(f"Error scraping case IDs: {str(e)}")
        return []

def scrape_case_details(case_id: str) -> Dict:
    """
    Scrape case details for a given case ID.
    """
    case_info_url = f"{settings.PAGE_URL.rstrip('/')}{settings.CASE_INFORMATION_URL}"
    
    logger.info(f"Starting to scrape details for case ID: {case_id}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': settings.PAGE_URL.rstrip('/'),
        'Referer': settings.PAGE_URL,
    }
    
    try:
        session = requests.Session()
        data = {
            'case_id': case_id,
            'screen': 'summary'
        }
        
        logger.info(f"Making request for case details to {case_info_url}")
        response = session.post(case_info_url, headers=headers, data=data)
        response.raise_for_status()
        logger.info(f"Successfully retrieved case details for case ID: {case_id}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize the case details dictionary
        case_details = {
            'case_id': case_id,
            'filing_type': '',
            'filing_date': '',
            'status': '',
            'plaintiff': '',
            'defendants': [],
            'parcel_number': '',
            'case_filing_id': '',
            'county': 'Montgomery',
            'property_address': ''
        }
        
        # Find all table cells that might contain our data
        cells = soup.find_all(['td', 'th'])
        
        for i, cell in enumerate(cells):
            cell_text = cell.text.strip()
            
            # Look for labels and their corresponding values
            if 'Case Action:' in cell_text or 'Case Type:' in cell_text:
                next_cell = cells[i + 1] if i + 1 < len(cells) else None
                if next_cell:
                    case_details['filing_type'] = next_cell.text.strip()
                    logger.info(f"Found filing type: {case_details['filing_type']}")
            
            elif 'File Date:' in cell_text:
                next_cell = cells[i + 1] if i + 1 < len(cells) else None
                if next_cell:
                    case_details['filing_date'] = next_cell.text.strip()
                    logger.info(f"Found filing date: {case_details['filing_date']}")
            
            elif 'Status:' in cell_text:
                next_cell = cells[i + 1] if i + 1 < len(cells) else None
                if next_cell:
                    case_details['status'] = next_cell.text.strip()
                    logger.info(f"Found status: {case_details['status']}")
            
            elif 'Property Address:' in cell_text:
                next_cell = cells[i + 1] if i + 1 < len(cells) else None
                if next_cell:
                    case_details['property_address'] = next_cell.text.strip()
                    logger.info(f"Found property address: {case_details['property_address']}")
        
        # Special handling for Parcel Number, PLAINTIFF, DEFENDANT, and CASE FILING ID
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                first_cell_text = cells[0].text.strip().upper()
                
                # Handle Parcel Number
                if 'PARCEL NUMBER' in first_cell_text:
                    case_details['parcel_number'] = cells[1].text.strip()
                    logger.info(f"Found parcel number: {case_details['parcel_number']}")
                
                # Handle PLAINTIFF
                elif first_cell_text.strip() == 'PLAINTIFF':
                    case_details['plaintiff'] = cells[1].text.strip()
                    logger.info(f"Found plaintiff: {case_details['plaintiff']}")
                
                # Handle DEFENDANT
                elif 'DEFENDANT' in first_cell_text:
                    defendant_text = cells[1].text.strip()
                    if defendant_text:
                        case_details['defendants'].append(defendant_text)
                        logger.info(f"Found defendant: {defendant_text}")
                
                # Handle CASE FILING ID
                elif 'CASE FILING ID' in first_cell_text:
                    case_details['case_filing_id'] = cells[1].text.strip()
                    logger.info(f"Found case filing ID: {case_details['case_filing_id']}")
        
        logger.info(f"Successfully scraped all details for case ID: {case_id}")
        logger.info("Case details summary:")
        logger.info(json.dumps(case_details, indent=2))
        
        return case_details
        
    except Exception as e:
        logger.error(f"Error scraping case details for case ID {case_id}: {e}")
        if 'response' in locals():
            logger.error(f"Response content: {response.text[:1000]}")
        return None

def save_to_database(data: List[Dict[str, str]]) -> None:
    """
    Save the scraped data to the database.
    """
    try:
        logger.info("Starting to save data to database")
        db = next(get_db())
        
        # Create the table if it doesn't exist
        logger.info("Ensuring foreclosure_cases table exists")
        ForeclosureCase.__table__.create(db.get_bind(), checkfirst=True)
        logger.info("Foreclosure_cases table exists or was created successfully")
        
        # Track how many new cases were added
        new_cases_added = 0
        
        for case in data:
            if not case:
                continue
                
            # Check if case_id already exists
            existing_case = db.query(ForeclosureCase).filter(
                ForeclosureCase.case_id == case['case_id']
            ).first()
            
            if not existing_case:
                # Create new case
                new_case = ForeclosureCase(**case)
                db.add(new_case)
                new_cases_added += 1
                logger.info(f"Successfully saved case {case['case_id']} to database")
            else:
                logger.info(f"Case ID {case['case_id']} already exists in database, skipping...")
        
        # Commit the transaction
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
    Run the foreclosure scraper.
    """
    try:
        logger.info("Starting foreclosure scraper")
        
        # Get recaptcha token
        logger.info("Getting reCAPTCHA token")
        captcha_token = get_recaptcha_token()
        if not captcha_token:
            logger.error("Failed to get reCAPTCHA token")
            return
        logger.info("Successfully obtained reCAPTCHA token")
        
        # Scrape the case IDs
        case_ids = scrape_case_ids(captcha_token)
        logger.info(f"Found {len(case_ids)} cases to process")
        
        # Process each case ID and collect details
        case_details_list = []
        for case_id in case_ids:
            logger.info(f"\nProcessing case ID: {case_id}")
            case_details = scrape_case_details(case_id)
            if case_details:
                case_details_list.append(case_details)
                logger.info(f"Successfully processed case ID: {case_id}")
            else:
                logger.error(f"Failed to process case ID: {case_id}")
        
        logger.info(f"Successfully processed {len(case_details_list)} cases")
        
        # Save to database
        logger.info("Starting to save cases to database")
        save_to_database(case_details_list)
        logger.info("Scraping process completed successfully")
        
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")
        raise

if __name__ == "__main__":
    run_scraper()
