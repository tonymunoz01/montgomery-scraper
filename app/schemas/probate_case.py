from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class ProbateCaseBase(BaseModel):
    decedent_name: str
    filing_date: date
    case_number: str
    source_url: str
    county: str = "Montgomery County, Ohio"
    property_address: Optional[str] = None

class ProbateCaseCreate(ProbateCaseBase):
    pass

class ProbateCase(ProbateCaseBase):
    id: str
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    class Config:
        from_attributes = True 