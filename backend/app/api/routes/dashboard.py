from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.dashboard import (
    DashboardInsightsResponse,
    DashboardOverviewResponse,
    GeographicAnalysisResponse,
    MetricKey,
    TrendsPatternsResponse,
)
from app.services.official_service import (
    get_dashboard_insights,
    get_geographic_analysis,
    get_overview,
    get_trends_patterns,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
def read_overview(
    year: Optional[int] = Query(default=None),
    metric: MetricKey = Query(default="count"),
    db: Session = Depends(get_db),
) -> DashboardOverviewResponse:
    """Return verified NCRB Overview KPIs, national trends, top states, and provenance."""
    return get_overview(db, year=year, metric=metric)


@router.get("/geographic", response_model=GeographicAnalysisResponse)
def read_geographic(
    year: Optional[int] = Query(default=None),
    metric: MetricKey = Query(default="rate_per_100k"),
    region: str = Query(default="ALL"),
    search: str = Query(default=""),
    db: Session = Depends(get_db),
) -> GeographicAnalysisResponse:
    """Return verified State/UT rankings, denominators, and explicit unavailability notes."""
    return get_geographic_analysis(db, year=year, metric=metric, region=region, search=search)


@router.get("/trends", response_model=TrendsPatternsResponse)
def read_trends(
    start_year: Optional[int] = Query(default=None),
    end_year: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> TrendsPatternsResponse:
    """Return longitudinal national series, structural breakdowns (3A.3/3A.4), and YoY shifts."""
    return get_trends_patterns(db, start_year=start_year, end_year=end_year)


@router.get("/insights", response_model=DashboardInsightsResponse)
def read_insights(
    year: Optional[int] = Query(default=None),
    state_code: str = Query(default="ALL"),
    metric: MetricKey = Query(default="count"),
    compare_code: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> DashboardInsightsResponse:
    """Return deterministic, source-traceable insights computed from validated DB records."""
    return get_dashboard_insights(
        db,
        year=year,
        state_code=state_code,
        metric=metric,
        compare_code=compare_code,
    )
