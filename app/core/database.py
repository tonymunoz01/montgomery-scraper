from typing import Generator
import psycopg2
from psycopg2.extras import RealDictCursor
from loguru import logger

from app.core.config import settings

def get_db() -> Generator:
    """
    Get database connection from pool
    """
    conn = None
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()