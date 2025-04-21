"""
Foreclosure Scraper Module

This module contains functions for scraping foreclosure case data from the court website.
"""
import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict
import re
import os
from loguru import logger

from app.core.config import settings
from app.core.database import get_db

def get_search_results(captcha_token: str) -> str:
    """
    Make a request to the backend with the recaptcha token and get the HTML response.
    """
    try:
        # First get the initial page to get VIEWSTATE and EVENTVALIDATION
        session = requests.Session()
        initial_response = session.get(settings.PAGE_URL)
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
            'ctl00$ContentPlaceHolder1$txtCaseType': '',
            'ctl00$ContentPlaceHolder1$txtCaseStatus': '',
            'ctl00$ContentPlaceHolder1$txtFilingDateFrom': '',
            'ctl00$ContentPlaceHolder1$txtFilingDateTo': '',
            'ctl00$ContentPlaceHolder1$btnSearch': 'Search'
        }
        
        # Make the actual request
        response = session.post(settings.GENERAL_SEARCH_RESULTS_URL, headers={
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
        }, data=data)
        response.raise_for_status()
        
        return response.text
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request: {e}")
        if hasattr(e, 'response'):
            logger.error(f"Response Status Code: {e.response.status_code}")
            logger.error(f"Response Headers: {e.response.headers}")
            logger.error(f"Response Content: {e.response.text[:1000]}")
        return ""

def scrape_case_ids(captcha_token: str) -> List[str]:
    """
    Scrape case IDs from the HTML response where the row contains both MORTGAGE FORECLOSURE (MF)
    and OPEN status with text-success class. Extracts case_id from onclick attribute.
    """
    try:
        # Get HTML content from backend
        html_content = get_search_results(captcha_token)
        if not html_content:
            logger.error("Failed to get HTML content")
            return []
        
        # Parse the HTML content
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all table rows
        rows = soup.find_all('tr')
        
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
        
        return case_data
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return []

def scrape_case_details(case_id: str) -> Dict:
    """
    Scrape case details for a given case ID.
    """
    try:
        session = requests.Session()
        data = {
            'case_id': case_id,
            'screen': 'summary'
        }
        
        response = session.post(f"{settings.PAGE_URL.rstrip('/')}/Helpers/caseInformation.aspx", headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': settings.PAGE_URL.rstrip('/'),
            'Referer': settings.PAGE_URL,
        }, data=data)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize the case details dictionary with snake_case keys
        case_details = {
            'case_id': case_id,
            'filing_type': '',
            'filing_date': '',
            'status': '',
            'plaintiff': '',
            'defendants': [],
            'parcel_number': '',
            'case_filing_id': '',
            'county': 'Montgomery'
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
            
            elif 'File Date:' in cell_text:
                next_cell = cells[i + 1] if i + 1 < len(cells) else None
                if next_cell:
                    case_details['filing_date'] = next_cell.text.strip()
            
            elif 'Status:' in cell_text:
                next_cell = cells[i + 1] if i + 1 < len(cells) else None
                if next_cell:
                    case_details['status'] = next_cell.text.strip()
        
        # Special handling for Parcel Number, PLAINTIFF, DEFENDANT, and CASE FILING ID
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                first_cell_text = cells[0].text.strip().upper()
                
                # Handle Parcel Number
                if 'PARCEL NUMBER' in first_cell_text:
                    case_details['parcel_number'] = cells[1].text.strip()
                
                # Handle PLAINTIFF
                elif first_cell_text.strip() == 'PLAINTIFF':
                    case_details['plaintiff'] = cells[1].text.strip()
                
                # Handle DEFENDANT
                elif 'DEFENDANT' in first_cell_text:
                    defendant_text = cells[1].text.strip()
                    if defendant_text:
                        case_details['defendants'].append(defendant_text)
                
                # Handle CASE FILING ID
                elif 'CASE FILING ID' in first_cell_text:
                    case_details['case_filing_id'] = cells[1].text.strip()
        
        return case_details
        
    except Exception as e:
        logger.error(f"Error scraping case details for case ID {case_id}: {e}")
        return None

def save_to_postgresql(data: List[Dict[str, str]]) -> None:
    """
    Save the scraped data to PostgreSQL database.
    Only saves data for case_ids that don't already exist in the database.
    """
    conn = None
    cur = None
    try:
        # Get database connection from generator
        db_gen = get_db()
        conn = next(db_gen)
        cur = conn.cursor()
        
        # Create table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS foreclosure_cases (
                id SERIAL PRIMARY KEY,
                case_id VARCHAR(100),
                filing_type VARCHAR(255),
                filing_date DATE,
                status VARCHAR(100),
                plaintiff VARCHAR(255),
                defendants JSONB,
                parcel_number VARCHAR(100),
                case_filing_id VARCHAR(100),
                county VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Track how many new cases were added
        new_cases_added = 0
        
        # Insert data
        for case in data:
            if not case:  # Skip if case is None
                continue
                
            # Check if case_id already exists
            cur.execute("""
                SELECT case_id FROM foreclosure_cases WHERE case_id = %s
            """, (case['case_id'],))
            
            if cur.fetchone() is None:
                # Case doesn't exist, insert it
                cur.execute("""
                    INSERT INTO foreclosure_cases 
                    (case_id, filing_type, filing_date, status, plaintiff, defendants, 
                     parcel_number, case_filing_id, county)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    case['case_id'],
                    case['filing_type'],
                    case['filing_date'],
                    case['status'],
                    case['plaintiff'],
                    json.dumps(case['defendants']),
                    case['parcel_number'],
                    case['case_filing_id'],
                    case['county']
                ))
                new_cases_added += 1
                logger.info(f"Successfully saved case {case['case_id']} to database")
            else:
                logger.info(f"Case ID {case['case_id']} already exists in database, skipping...")
        
        # Commit the transaction
        conn.commit()
        logger.info(f"Successfully saved {new_cases_added} new cases to PostgreSQL database")
        
    except Exception as e:
        logger.error(f"Error saving to PostgreSQL: {e}")
        if conn:
            conn.rollback()
        raise  # Re-raise the exception to handle it in the calling function
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close() 