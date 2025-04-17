import time
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv('CAPMONSTER_API_KEY')
SITE_KEY = os.getenv('RECAPTCHA_SITE_KEY')
PAGE_URL = os.getenv('PAGE_URL')
ACTION = os.getenv('RECAPTCHA_ACTION')
MIN_SCORE = float(os.getenv('RECAPTCHA_MIN_SCORE', '0.3'))

# API URLs
CAPMONSTER_BASE_URL = os.getenv('CAPMONSTER_BASE_URL')
CREATE_TASK_URL = f"{CAPMONSTER_BASE_URL}{os.getenv('CAPMONSTER_CREATE_TASK_URL')}"
GET_RESULT_URL = f"{CAPMONSTER_BASE_URL}{os.getenv('CAPMONSTER_GET_RESULT_URL')}"

def get_recaptcha_token() -> str:
    """
    Get a solved reCAPTCHA token using CapMonster API.
    Returns the token as a string, or empty string if failed.
    """
    try:
        # Step 1: Create Task
        task_payload = {
            "clientKey": API_KEY,
            "task": {
                "type": "RecaptchaV3TaskProxyless",
                "websiteURL": PAGE_URL,
                "websiteKey": SITE_KEY,
                "minScore": MIN_SCORE,
                "pageAction": ACTION
            }
        }

        response = requests.post(CREATE_TASK_URL, json=task_payload)
        task_id = response.json().get('taskId')
        if not task_id:
            print("Failed to create task")
            return ""

        # Step 2: Poll for Result
        while True:
            time.sleep(5)
            result_response = requests.post(GET_RESULT_URL, json={
                "clientKey": API_KEY,
                "taskId": task_id
            })
            result = result_response.json()
            if result.get('status') == 'ready':
                token = result['solution']['gRecaptchaResponse']
                return token
            elif result.get('status') == 'failed':
                print("Task failed")
                return ""

    except Exception as e:
        print(f"Error getting recaptcha token: {e}")
        return ""

if __name__ == "__main__":
    token = get_recaptcha_token()
    if token:
        print("Got the reCAPTCHA Solved Token:")
    else:
        print("Failed to get token")
