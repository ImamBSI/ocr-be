import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from config import settings
import logging

logger = logging.getLogger(__name__)

# ==================== Database URL Configuration ====================
DATABASE_URL = settings.DATABASE_URL

# Determine if using SQLite (for development)
IS_SQLITE = "sqlite" in DATABASE_URL

# ==================== Engine Configuration ====================
if IS_SQLITE:
    # SQLite configuration (development)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG,
    )
else:
    # PostgreSQL or other databases (production)
    engine = create_engine(
        DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        echo=settings.DEBUG,
    )

# ==================== Enable Foreign Keys for SQLite ====================
if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ==================== Session Configuration ====================
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ==================== Dependency for FastAPI ====================
def get_db() -> Session:
    """
    Dependency for FastAPI to get database session.
    
    Usage in routes:
    @app.get("/items")
    def get_items(db: Session = Depends(get_db)):
        return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== Database Initialization ====================
def init_db():
    """
    Initialize database by creating all tables.
    Run this once to setup the database.
    """
    # Import all models here to register them with Base.metadata
    from models import Base
    
    logger.info(f"Initializing database: {DATABASE_URL}")
    
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        logger.info(f"Uploads directory ensured: {settings.UPLOAD_DIR}")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


# ==================== Database Health Check ====================
def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False