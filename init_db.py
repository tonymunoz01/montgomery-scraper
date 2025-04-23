from app.core.database import init_db
from loguru import logger

if __name__ == "__main__":
    try:
        # Initialize the database and create all tables
        init_db()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise 