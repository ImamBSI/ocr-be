import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.api_router import api_router
from app.core.config import settings
from app.db.session import check_db_connection, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting OCR Recruitment System")
    logger.info(f"API Prefix: {settings.API_STR}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(f"Database: {settings.DATABASE_URL}")

    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")

    if check_db_connection():
        logger.info("Database connection verified")
    else:
        logger.warning("Database connection check failed")

    yield

    logger.info("Shutting down OCR Recruitment System")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="OCR-based Recruitment System for CV Grading",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.error(f"ValueError: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(api_router, prefix=settings.API_STR.rstrip("/"))


@app.get("/")
async def root():
    """Root endpoint dengan API information."""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "api_prefix": settings.API_STR,
    }


@app.get("/debug/config")
async def debug_config():
    """Debug endpoint untuk menampilkan configuration (hanya saat debug)."""
    if not settings.DEBUG:
        return {"error": "Not available in production"}

    return {
        "project_name": settings.PROJECT_NAME,
        "api_prefix": settings.API_STR,
        "debug": settings.DEBUG,
        "upload_dir": settings.UPLOAD_DIR,
        "allowed_file_types": settings.ALLOWED_FILE_TYPES,
        "ocr_engine": settings.OCR_ENGINE,
        "database_type": (
            "SQLite" if "sqlite" in settings.DATABASE_URL else "PostgreSQL"
        ),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )