from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.config import get_settings
from app.database.session import SessionLocal, check_database_health, engine
from app.models.records import CrimeStatistic
from app.schemas.dashboard import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Health check endpoint")
def health_check() -> HealthResponse:
    """Return service health, database connectivity, and official ingestion status."""
    settings = get_settings()
    db_ok = check_database_health()
    verified_count = 0
    latest_granular = None
    latest_pub = None

    if db_ok:
        try:
            with SessionLocal() as db:
                verified_count = int(db.scalar(select(func.count(CrimeStatistic.id))) or 0)
                latest_pub = db.scalar(select(func.max(CrimeStatistic.reporting_year)))
                latest_granular = db.scalar(
                    select(func.max(CrimeStatistic.reporting_year)).where(
                        CrimeStatistic.crime_domain == "rape_ipc_376",
                        CrimeStatistic.sub_category == "Total",
                    )
                )
        except Exception:
            pass

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database_connected=db_ok,
        database_dialect=engine.dialect.name,
        data_mode="VERIFIED_OFFICIAL_PHASE_2" if verified_count > 0 else "EMPTY_AWAITING_INGESTION",
        verified_records_count=verified_count,
        latest_granular_year=latest_granular,
        latest_publication_year=latest_pub,
        timestamp=datetime.now(timezone.utc),
    )
