from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MontgomeryDivorceCaseBase(BaseModel):
    case_id: str
    case_number: str
    plaintiff: str
    defendant: str
    filing_date: str
    status: str
    county: str
    property_address: Optional[str] = None

class MontgomeryDivorceCaseCreate(MontgomeryDivorceCaseBase):
    pass

class MontgomeryDivorceCase(MontgomeryDivorceCaseBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True 