import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict
import re
import os
from dotenv import load_dotenv
from recaptcha import get_recaptcha_token  # We'll create this function in recaptcha.py
import psycopg2
from psycopg2.extras import Json

# Load environment variables
load_dotenv()

# Get database configuration from environment variables
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def get_search_results(captcha_token: str) -> str:
    """
    Make a request to the backend with the recaptcha token and get the HTML response.
    """

    general_search_results_url = os.getenv('GENERAL_SEARCH_RESULTS_URL')
    base_url = os.getenv('PAGE_URL')
    
    # Updated headers to match what a browser would send
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': base_url.rstrip('/'),
        'Referer': base_url,
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
    }
    
    try:
        # First get the initial page to get VIEWSTATE and EVENTVALIDATION
        session = requests.Session()
        initial_response = session.get(base_url)
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
        response = session.post(general_search_results_url, headers=headers, data=data)
        response.raise_for_status()
        
        # Print response details for debugging
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Content Length: {len(response.text)}")
        
        return response.text
        
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        if hasattr(e, 'response'):
            print(f"Response Status Code: {e.response.status_code}")
            print(f"Response Headers: {e.response.headers}")
            print(f"Response Content: {e.response.text[:1000]}")  # Print first 1000 chars of error response
        return ""

def scrape_case_ids() -> List[Dict[str, str]]:
    """
    Scrape case IDs from the HTML response where the row contains both MORTGAGE FORECLOSURE (MF)
    and OPEN status with text-success class. Extracts case_id from onclick attribute.
    """
    try:
        # Get recaptcha token
        captcha_token = get_recaptcha_token()
        if not captcha_token:
            print("Failed to get recaptcha token")
            return []
            
        # Get HTML content from backend
        html_content = get_search_results(captcha_token)
        if not html_content:
            print("Failed to get HTML content")
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
        print(f"An error occurred: {e}")
        return []

def save_to_json(data: List[Dict[str, str]], filename: str = 'case_data.json') -> None:
    """
    Save the scraped data to a JSON file.
    """
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Error saving to JSON file: {e}")

def scrape_case_details(case_id: str) -> Dict:
    """
    Scrape case details for a given case ID.
    """
    base_url = os.getenv('PAGE_URL')
    case_info_url = f"{base_url.rstrip('/')}/Helpers/caseInformation.aspx"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': base_url.rstrip('/'),
        'Referer': base_url,
    }
    
    try:
        session = requests.Session()
        data = {
            'case_id': case_id,
            'screen': 'summary'
        }
        
        response = session.post(case_info_url, headers=headers, data=data)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize the case details dictionary
        case_details = {
            'Filing Type': '',
            'Filling Date': '',
            'Status': '',
            'PLAINTIFF': '',
            'Defendants': [],
            'Parcel Number': '',
            'CASE FILING ID': '',
            'Source URL': '',
            'County': 'Montgomery'
        }
        
        # Find all table cells that might contain our data
        cells = soup.find_all(['td', 'th'])
        
        for i, cell in enumerate(cells):
            cell_text = cell.text.strip()
            
            # Look for labels and their corresponding values
            if 'Case Action:' in cell_text or 'Case Type:' in cell_text:
                next_cell = cells[i + 1] if i + 1 < len(cells) else None
                if next_cell:
                    case_details['Filing Type'] = next_cell.text.strip()
            
            elif 'File Date:' in cell_text:
                next_cell = cells[i + 1] if i + 1 < len(cells) else None
                if next_cell:
                    case_details['Filling Date'] = next_cell.text.strip()
            
            elif 'Status:' in cell_text:
                next_cell = cells[i + 1] if i + 1 < len(cells) else None
                if next_cell:
                    case_details['Status'] = next_cell.text.strip()
        
        # Special handling for Parcel Number, PLAINTIFF, DEFENDANT, and CASE FILING ID
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                first_cell_text = cells[0].text.strip().upper()
                
                # Handle Parcel Number
                if 'PARCEL NUMBER' in first_cell_text:
                    case_details['Parcel Number'] = cells[1].text.strip()
                
                # Handle PLAINTIFF
                elif first_cell_text.strip() == 'PLAINTIFF':
                    case_details['PLAINTIFF'] = cells[1].text.strip()
                
                # Handle DEFENDANT
                elif 'DEFENDANT' in first_cell_text:
                    defendant_text = cells[1].text.strip()
                    if defendant_text:
                        case_details['Defendants'].append(defendant_text)
                
                # Handle CASE FILING ID
                elif 'CASE FILING ID' in first_cell_text:
                    case_details['CASE FILING ID'] = cells[1].text.strip()
        
        # Print the case details for debugging
        print(f"Successfully scraped case ID {case_id}:")
        print(json.dumps(case_details, indent=2))
        
        # Print the raw HTML for debugging if we're missing important data
        if not case_details['Parcel Number'] or not case_details['PLAINTIFF'] or not case_details['Defendants'] or not case_details['CASE FILING ID']:
            print("\nDebugging - Raw HTML snippet:")
            print(response.text[:2000])  # Print first 2000 characters of the response
        
        return case_details
        
    except Exception as e:
        print(f"Error scraping case details for case ID {case_id}: {e}")
        print(f"Response content: {response.text[:1000] if 'response' in locals() else 'No response'}")
        return None

def save_to_postgresql(data: List[Dict[str, str]]) -> None:
    """
    Save the scraped data to PostgreSQL database.
    """
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        
        # Create table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS foreclosure_cases (
                id SERIAL PRIMARY KEY,
                filing_type VARCHAR(255),
                filing_date DATE,
                status VARCHAR(100),
                plaintiff VARCHAR(255),
                defendants JSONB,
                parcel_number VARCHAR(100),
                case_filing_id VARCHAR(100),
                source_url VARCHAR(255),
                county VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert data
        for case in data:
            cur.execute("""
                INSERT INTO foreclosure_cases 
                (filing_type, filing_date, status, plaintiff, defendants, parcel_number, 
                 case_filing_id, source_url, county)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                case['Filing Type'],
                case['Filling Date'],
                case['Status'],
                case['PLAINTIFF'],
                Json(case['Defendants']),
                case['Parcel Number'],
                case['CASE FILING ID'],
                case['Source URL'],
                case['County']
            ))
        
        # Commit the transaction
        conn.commit()
        print(f"Successfully saved {len(data)} cases to PostgreSQL database")
        
    except Exception as e:
        print(f"Error saving to PostgreSQL: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # Scrape the case IDs
    case_ids = scrape_case_ids()
    print(f"Found {len(case_ids)} cases to process")
    
    # Process each case ID and collect details
    case_details_list = []
    for case_id in case_ids:
        print(f"\nProcessing case ID: {case_id}")
        case_details = scrape_case_details(case_id)
        if case_details:
            case_details_list.append(case_details)
    
    # Save to PostgreSQL database
    save_to_postgresql(case_details_list)
    print(f"\nSuccessfully saved {len(case_details_list)} case details to PostgreSQL database")
