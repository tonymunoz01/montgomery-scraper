import requests
import time
from loguru import logger
from app.core.config import settings

def get_recaptcha_token() -> str:
    """
    Get reCAPTCHA token using CapMonster service.
    """
    try:
        logger.info("Starting reCAPTCHA token generation")
        
        # Create task
        create_task_url = f"{settings.CAPMONSTER_BASE_URL}{settings.CAPMONSTER_CREATE_TASK_URL}"
        task_data = {
            "clientKey": settings.CAPMONSTER_API_KEY,
            "task": {
                "type": "RecaptchaV3TaskProxyless",
                "websiteURL": settings.PAGE_URL,
                "websiteKey": settings.RECAPTCHA_SITE_KEY,
                "minScore": settings.RECAPTCHA_MIN_SCORE,
                "pageAction": settings.RECAPTCHA_ACTION
            }
        }
        
        logger.info("Creating reCAPTCHA task")
        response = requests.post(create_task_url, json=task_data)
        response.raise_for_status()
        task_id = response.json()["taskId"]
        logger.info(f"Created task with ID: {task_id}")
        
        # Get task result
        get_result_url = f"{settings.CAPMONSTER_BASE_URL}{settings.CAPMONSTER_GET_RESULT_URL}"
        result_data = {
            "clientKey": settings.CAPMONSTER_API_KEY,
            "taskId": task_id
        }
        
        # Poll for result
        max_attempts = 30
        attempt = 0
        while attempt < max_attempts:
            logger.info(f"Checking task result (attempt {attempt + 1}/{max_attempts})")
            response = requests.post(get_result_url, json=result_data)
            response.raise_for_status()
            result = response.json()
            
            if result["status"] == "ready":
                token = result["solution"]["gRecaptchaResponse"]
                logger.info("Successfully obtained reCAPTCHA token")
                return token
            
            time.sleep(2)  # Wait 2 seconds before next attempt
            attempt += 1
        
        logger.error("Failed to get reCAPTCHA token: Timeout")
        return ""
        
    except Exception as e:
        logger.error(f"Error getting reCAPTCHA token: {str(e)}")
        return "" 