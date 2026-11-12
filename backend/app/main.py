from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.database.session import SessionLocal, init_db
from app.services.official_service import ensure_official_data

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize SQLite schema and ensure verified NCRB official datasets are ingested."""
    init_db()
    with SessionLocal() as db:
        ensure_official_data(db)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Investigative Data Dashboard API for THE UNHEARD (Verified Official Data).",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", tags=["root"])
    def root() -> dict:
        return {
            "project": "THE UNHEARD",
            "tagline": "Behind every number, there is a story.",
            "health": f"{settings.api_prefix}/health",
        }

    return app


app = create_app()

