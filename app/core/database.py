from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger
from sqlalchemy import inspect

from app.core.config import settings
from app.core.base import Base

SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(recreate: bool = False):
    """Initialize the database by creating all tables
    
    Args:
        recreate (bool): If True, drop all tables before creating them
    """
    try:
        # Import all models here to avoid circular imports
        from app.models.probate_case import ProbateCase
        from app.models.foreclosure_case import ForeclosureCase
        from app.models.divorce_case import DivorceCase
        
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if recreate:
            Base.metadata.drop_all(bind=engine)
            logger.info("Dropped all existing tables")
        elif existing_tables:
            logger.info("Tables already exist, skipping creation")
            return
            
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def get_db():
    """
    Get database session and ensure tables exist
    """
    try:
        # Ensure tables exist before getting session
        init_db(recreate=False)
        
        db = SessionLocal()
        try:
            yield db
        except Exception as e:
            logger.error(f"Database session error: {e}")
            raise
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting database session: {e}")
        raise