import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict
import re
import os
from dotenv import load_dotenv
from recaptcha import get_recaptcha_token  # We'll create this function in recaptcha.py

# Load environment variables
load_dotenv()

def get_search_results(captcha_token: str) -> str:
    """
    Make a request to the backend with the recaptcha token and get the HTML response.
    """
    print("reCAPTCHA Solved Token:", captcha_token)
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

if __name__ == "__main__":
    # Scrape the case IDs from local index.html
    case_data = scrape_case_ids()
    
    # Save to JSON file
    save_to_json(case_data)
