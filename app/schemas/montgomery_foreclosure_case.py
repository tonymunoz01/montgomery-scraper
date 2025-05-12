from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class MontgomeryForeclosureCaseBase(BaseModel):
    case_id: str
    filing_type: str
    filing_date: str
    status: str
    plaintiff: str
    defendants: List[str]
    parcel_number: str
    case_filing_id: str
    county: str
    property_address: str

class MontgomeryForeclosureCaseCreate(MontgomeryForeclosureCaseBase):
    pass

class MontgomeryForeclosureCase(MontgomeryForeclosureCaseBase):
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True 