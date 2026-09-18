from fastapi import APIRouter

from app.api.routes import cv, jobs, scoring, system, upload

api_router = APIRouter()
api_router.include_router(upload.router)
api_router.include_router(cv.router)
api_router.include_router(scoring.router)
api_router.include_router(jobs.router)
api_router.include_router(system.router)