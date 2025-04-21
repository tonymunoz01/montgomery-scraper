from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl

class Settings(BaseSettings):
    PROJECT_NAME: str = "Foreclosure Case Scraper API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API for scraping and managing foreclosure case data from court websites"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    
    # Scraping
    PAGE_URL: str
    GENERAL_SEARCH_RESULTS_URL: str
    RECAPTCHA_SITE_KEY: str
    RECAPTCHA_ACTION: str
    RECAPTCHA_MIN_SCORE: float = 0.3
    
    # CapMonster
    CAPMONSTER_API_KEY: str
    CAPMONSTER_BASE_URL: str = "https://api.capmonster.cloud"
    CAPMONSTER_CREATE_TASK_URL: str = "/createTask"
    CAPMONSTER_GET_RESULT_URL: str = "/getTaskResult"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields in the .env file

settings = Settings() 