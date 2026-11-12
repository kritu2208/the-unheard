from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.dashboard import DataQualityReportResponse, DatasetListResponse
from app.services.official_service import get_data_quality_report, get_datasets_report

datasets_router = APIRouter(prefix="/datasets", tags=["datasets"])
quality_router = APIRouter(prefix="/data-quality", tags=["data-quality"])


@datasets_router.get("", response_model=DatasetListResponse)
def read_datasets(db: Session = Depends(get_db)) -> DatasetListResponse:
    """Return all ingested official dataset versions, SHA-256 hashes, and record counts."""
    return get_datasets_report(db)


@quality_router.get("", response_model=DataQualityReportResponse)
def read_data_quality(db: Session = Depends(get_db)) -> DataQualityReportResponse:
    """Return automated validation, cross-total, outlier, and coverage gap issues."""
    return get_data_quality_report(db)

