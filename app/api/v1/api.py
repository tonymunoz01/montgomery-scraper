from fastapi import APIRouter

from app.api.v1.endpoints import montgomery_foreclosure_cases, montgomery_probate_cases, montgomery_divorce_cases

api_router = APIRouter()

api_router.include_router(montgomery_foreclosure_cases.router, prefix="/foreclosure-cases", tags=["foreclosure-cases"])
api_router.include_router(montgomery_probate_cases.router, prefix="/probate-cases", tags=["probate-cases"])
api_router.include_router(montgomery_divorce_cases.router, prefix="/divorce-cases", tags=["divorce-cases"]) 