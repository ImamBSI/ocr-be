from fastapi import APIRouter, Depends

from app.api.deps import verify_api_key
from app.api.routes import cv, jobs, scoring, system, upload

# Semua route di bawah /api/* dilindungi API key (jika API_KEY di-set).
api_router = APIRouter(dependencies=[Depends(verify_api_key)])
api_router.include_router(upload.router)
api_router.include_router(cv.router)
api_router.include_router(scoring.router)
api_router.include_router(jobs.router)
api_router.include_router(system.router)
