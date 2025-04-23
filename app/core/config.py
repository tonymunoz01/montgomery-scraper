from typing import List
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Court Case Scraper API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API for scraping and managing court case data from Montgomery County, Ohio court website"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    
    # Court Website URLs
    PAGE_URL: str
    GENERAL_SEARCH_RESULTS_URL: str
    CASE_INFORMATION_URL: str = "/Helpers/caseInformation.aspx"
    
    # reCAPTCHA Settings
    RECAPTCHA_SITE_KEY: str
    RECAPTCHA_ACTION: str
    RECAPTCHA_MIN_SCORE: float = 0.5
    
    # CapMonster Settings
    CAPMONSTER_API_KEY: str
    CAPMONSTER_BASE_URL: str = "https://api.capmonster.cloud"
    CAPMONSTER_CREATE_TASK_URL: str = "/createTask"
    CAPMONSTER_GET_RESULT_URL: str = "/getTaskResult"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields in the .env file

settings = Settings() 