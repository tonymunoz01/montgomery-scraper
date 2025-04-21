from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class ForeclosureCaseBase(BaseModel):
    case_id: str
    filing_type: str
    filing_date: str
    status: str
    plaintiff: str
    defendants: List[str]
    parcel_number: str
    case_filing_id: str
    county: str

class ForeclosureCaseCreate(ForeclosureCaseBase):
    pass

class ForeclosureCase(ForeclosureCaseBase):
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True 