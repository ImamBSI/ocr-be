import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from config import settings
from database.connection import init_db, check_db_connection

# Import all routes
from routes import upload, cv, scoring, jobs, system

# ==================== Logging Configuration ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== Lifespan Handler ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown
    """
    # Startup
    logger.info("Starting OCR Recruitment System")
    logger.info(f"API Prefix: {settings.API_STR}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
    
    # Check database connection
    if check_db_connection():
        logger.info("Database connection verified")
    else:
        logger.warning("Database connection check failed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down OCR Recruitment System")


# ==================== FastAPI App ====================
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="OCR-based Recruitment System for CV Grading",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ==================== CORS Middleware ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# ==================== Error Handlers ====================
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions"""
    logger.error(f"ValueError: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ==================== Routes ====================
# Include all route modules
app.include_router(upload.router)
app.include_router(cv.router)
app.include_router(scoring.router)
app.include_router(jobs.router)
app.include_router(system.router)


# ==================== Root Endpoint ====================
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "api_prefix": settings.API_STR,
    }


# ==================== Debug Routes ====================
@app.get("/debug/config")
async def debug_config():
    """Debug endpoint to show configuration (only in debug mode)"""
    if not settings.DEBUG:
        return {"error": "Not available in production"}
    
    return {
        "project_name": settings.PROJECT_NAME,
        "api_prefix": settings.API_STR,
        "debug": settings.DEBUG,
        "upload_dir": settings.UPLOAD_DIR,
        "allowed_file_types": settings.ALLOWED_FILE_TYPES,
        "ocr_engine": settings.OCR_ENGINE,
        "database_type": "SQLite" if "sqlite" in settings.DATABASE_URL else "PostgreSQL",
    }


# ==================== Run ====================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )