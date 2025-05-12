from sqlalchemy.orm import Session
from app.models.montgomery_probate_case import MontgomeryProbateCase
from app.schemas.montgomery_probate_case import MontgomeryProbateCaseCreate
import uuid
from loguru import logger

class MontgomeryProbateCaseService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_probate_case(self, probate_case: MontgomeryProbateCaseCreate) -> MontgomeryProbateCase:
        """Create a new probate case in the database"""
        try:
            logger.info(f"Creating new probate case: {probate_case.case_number}")
            
            # Convert Pydantic model to dict and handle date conversion
            case_data = probate_case.model_dump()
            
            # Create new case
            db_case = MontgomeryProbateCase(
                id=str(uuid.uuid4()),
                **case_data
            )
            
            # Add to database
            self.db.add(db_case)
            self.db.commit()
            self.db.refresh(db_case)
            
            logger.info(f"Successfully created probate case: {probate_case.case_number}")
            return db_case
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating probate case {probate_case.case_number}: {str(e)}")
            logger.exception("Full traceback:")
            raise
    
    def update_probate_case(self, probate_case: MontgomeryProbateCaseCreate) -> MontgomeryProbateCase:
        """Update an existing probate case in the database"""
        try:
            logger.info(f"Updating probate case: {probate_case.case_number}")
            
            # Get existing case
            db_case = self.db.query(MontgomeryProbateCase).filter(
                MontgomeryProbateCase.case_number == probate_case.case_number
            ).first()
            
            if not db_case:
                logger.error(f"Case not found for update: {probate_case.case_number}")
                raise ValueError(f"Case not found: {probate_case.case_number}")
            
            # Convert Pydantic model to dict and handle date conversion
            case_data = probate_case.model_dump()
            
            # Update case fields
            for key, value in case_data.items():
                setattr(db_case, key, value)
            
            # Save changes
            self.db.commit()
            self.db.refresh(db_case)
            
            logger.info(f"Successfully updated probate case: {probate_case.case_number}")
            return db_case
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating probate case {probate_case.case_number}: {str(e)}")
            logger.exception("Full traceback:")
            raise
    
    def get_probate_case(self, case_number: str) -> MontgomeryProbateCase:
        """Get a probate case by case number"""
        try:
            logger.info(f"Fetching probate case: {case_number}")
            case = self.db.query(MontgomeryProbateCase).filter(MontgomeryProbateCase.case_number == case_number).first()
            if case:
                logger.info(f"Found probate case: {case_number}")
            else:
                logger.info(f"Probate case not found: {case_number}")
            return case
        except Exception as e:
            logger.error(f"Error fetching probate case {case_number}: {str(e)}")
            logger.exception("Full traceback:")
            raise
    
    def get_all_probate_cases(self) -> list[MontgomeryProbateCase]:
        """Get all probate cases"""
        try:
            logger.info("Fetching all probate cases")
            cases = self.db.query(MontgomeryProbateCase).all()
            logger.info(f"Found {len(cases)} probate cases")
            return cases
        except Exception as e:
            logger.error(f"Error fetching all probate cases: {str(e)}")
            logger.exception("Full traceback:")
            raise
    
    def case_exists(self, case_number: str) -> bool:
        """Check if a case already exists in the database"""
        try:
            logger.info(f"Checking if case exists: {case_number}")
            exists = self.db.query(MontgomeryProbateCase).filter(MontgomeryProbateCase.case_number == case_number).first() is not None
            logger.info(f"Case {case_number} {'exists' if exists else 'does not exist'}")
            return exists
        except Exception as e:
            logger.error(f"Error checking if case exists {case_number}: {str(e)}")
            logger.exception("Full traceback:")
            raise 