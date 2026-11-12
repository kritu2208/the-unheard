from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.dashboard import SourcesMethodologyResponse
from app.services.official_service import get_sources_methodology

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=SourcesMethodologyResponse)
def read_sources_and_methodology(
    db: Session = Depends(get_db),
) -> SourcesMethodologyResponse:
    """Return official source registry, dataset versions, data-quality summary, and methodology."""
    return get_sources_methodology(db)
