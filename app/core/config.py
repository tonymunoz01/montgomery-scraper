from typing import List, Union
from pydantic import AnyHttpUrl, validator, Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Court Case Scraper API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API for scraping and managing court case data from Montgomery County, Ohio court website"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    # Set to True to allow requests from any origin (useful for development)
    ALLOW_ALL_ORIGINS: bool = Field(True, env="ALLOW_ALL_ORIGINS")  # Default to True for development
    
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://yourfrontenddomain.com",  # Replace with your actual frontend domain in production
    ]
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    
    # Court Website URLs
    PAGE_URL: str = "https://pro.mcohio.org"
    GENERAL_SEARCH_RESULTS_URL: str = "/Helpers/caseInformation.aspx"
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