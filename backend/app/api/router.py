from fastapi import APIRouter

from app.api.routes import ai, dashboard, datasets, health, research, sources

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(ai.router)
api_router.include_router(research.router)
api_router.include_router(sources.router)
api_router.include_router(datasets.datasets_router)
api_router.include_router(datasets.quality_router)
