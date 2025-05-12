from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ScrapingLog(BaseModel):
    id: str
    date_time: datetime
    source: str
    total_records: int
    success_status: bool
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True 