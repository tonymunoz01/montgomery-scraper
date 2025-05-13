from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from uuid import UUID

class ScrapingLog(BaseModel):
    id: UUID
    date_time: datetime
    source: str
    total_records: int
    success_status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "date_time": "2024-03-14T12:00:00",
                "source": "example_source",
                "total_records": 100,
                "success_status": 'True',
                "error_message": None,
                "created_at": "2024-03-14T12:00:00"
            }
        } 