import time
import requests
from loguru import logger
from urllib.parse import urljoin

from app.core.config import settings

def get_recaptcha_token() -> str:
    """
    Get a solved reCAPTCHA token using CapMonster API.
    Returns the token as a string, or empty string if failed.
    """
    try:
        # Step 1: Create Task
        task_payload = {
            "clientKey": settings.CAPMONSTER_API_KEY,
            "task": {
                "type": "RecaptchaV3TaskProxyless",
                "websiteURL": settings.PAGE_URL,
                "websiteKey": settings.RECAPTCHA_SITE_KEY,
                "minScore": settings.RECAPTCHA_MIN_SCORE,
                "pageAction": settings.RECAPTCHA_ACTION
            }
        }

        # Construct full URLs
        create_task_url = urljoin(settings.CAPMONSTER_BASE_URL, settings.CAPMONSTER_CREATE_TASK_URL)
        get_result_url = urljoin(settings.CAPMONSTER_BASE_URL, settings.CAPMONSTER_GET_RESULT_URL)

        logger.info(f"Creating task with URL: {create_task_url}")
        response = requests.post(create_task_url, json=task_payload)
        response.raise_for_status()
        
        task_id = response.json().get('taskId')
        if not task_id:
            logger.error("Failed to create task")
            return ""

        # Step 2: Poll for Result
        max_attempts = 10  # Maximum number of attempts
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(5)
            attempt += 1
            logger.info(f"Checking task result (attempt {attempt}/{max_attempts})")
            
            result_response = requests.post(get_result_url, json={
                "clientKey": settings.CAPMONSTER_API_KEY,
                "taskId": task_id
            })
            result_response.raise_for_status()
            result = result_response.json()
            
            if result.get('status') == 'ready':
                token = result['solution']['gRecaptchaResponse']
                logger.info("Successfully got recaptcha token")
                return token
            elif result.get('status') == 'failed':
                logger.error("Task failed")
                return ""
            
        logger.error(f"Max attempts ({max_attempts}) reached without getting a result")
        return ""

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error getting recaptcha token: {e}")
        if hasattr(e, 'response'):
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response content: {e.response.text[:500]}")
        return ""
    except Exception as e:
        logger.error(f"Error getting recaptcha token: {e}")
        return "" 