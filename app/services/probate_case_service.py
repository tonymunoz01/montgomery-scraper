from sqlalchemy.orm import Session
from app.models.probate_case import ProbateCase
from app.schemas.probate_case import ProbateCaseCreate
import uuid

class ProbateCaseService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_probate_case(self, probate_case: ProbateCaseCreate) -> ProbateCase:
        """Create a new probate case in the database"""
        db_case = ProbateCase(
            id=str(uuid.uuid4()),
            **probate_case.model_dump()
        )
        self.db.add(db_case)
        self.db.commit()
        self.db.refresh(db_case)
        return db_case
    
    def get_probate_case(self, case_number: str) -> ProbateCase:
        """Get a probate case by case number"""
        return self.db.query(ProbateCase).filter(ProbateCase.case_number == case_number).first()
    
    def get_all_probate_cases(self) -> list[ProbateCase]:
        """Get all probate cases"""
        return self.db.query(ProbateCase).all()
    
    def case_exists(self, case_number: str) -> bool:
        """Check if a case already exists in the database"""
        return self.db.query(ProbateCase).filter(ProbateCase.case_number == case_number).first() is not None 