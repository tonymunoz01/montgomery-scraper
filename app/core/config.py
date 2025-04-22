from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl

class Settings(BaseSettings):
    PROJECT_NAME: str = "Probate Case Scraper API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API for scraping and managing probate case data from Montgomery County, Ohio court website"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    
    # Probate Case Scraping
    PROBATE_CASE_SEARCH_URL: str = "https://go.mcohio.org/applications/probate/prodcfm/casesearch_actionx.cfm"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields in the .env file

settings = Settings() 