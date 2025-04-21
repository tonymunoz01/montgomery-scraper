from fastapi import APIRouter

from app.api.v1.endpoints import foreclosure_cases

api_router = APIRouter()

api_router.include_router(foreclosure_cases.router, prefix="/foreclosure-cases", tags=["foreclosure-cases"]) 