from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger
from sqlalchemy import inspect, Column, String

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
        
        # Create all tables if they don't exist
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Check for missing columns and add them
        inspector = inspect(engine)
        for table_name in Base.metadata.tables.keys():
            existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
            table = Base.metadata.tables[table_name]
            
            for column in table.columns:
                if column.name not in existing_columns:
                    logger.info(f"Adding missing column {column.name} to table {table_name}")
                    column_type = column.type.compile(engine.dialect)
                    nullable = "NULL" if column.nullable else "NOT NULL"
                    default = f"DEFAULT {column.default.arg}" if column.default else ""
                    engine.execute(f"ALTER TABLE {table_name} ADD COLUMN {column.name} {column_type} {nullable} {default}")
                    logger.info(f"Successfully added column {column.name} to table {table_name}")
        
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