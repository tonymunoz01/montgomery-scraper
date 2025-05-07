from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class ProbateCaseBase(BaseModel):
    decedent_name: str
    filing_date: date
    case_number: str
    case_status: str
    source_url: str
    county: str = "Montgomery County, Ohio"
    property_address: Optional[str] = None
    fiduciary_name: Optional[str] = None
    fiduciary_address: Optional[str] = None
    fiduciary_city: Optional[str] = None
    fiduciary_zip: Optional[str] = None

class ProbateCaseCreate(ProbateCaseBase):
    pass

class ProbateCase(ProbateCaseBase):
    id: str
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    class Config:
        from_attributes = True 