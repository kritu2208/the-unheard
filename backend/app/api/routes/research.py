from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.dashboard import MetricKey, ResearchPreviewRequest, ResearchPreviewResponse
from app.services.official_service import build_research_preview
from app.services.pdf_service import generate_single_page_pdf

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/preview", response_model=ResearchPreviewResponse)
def generate_research_preview(
    payload: ResearchPreviewRequest,
    db: Session = Depends(get_db),
) -> ResearchPreviewResponse:
    """Filter verified official State/UT records and generate citation-embedded CSV output."""
    return build_research_preview(db, payload)


@router.get("/pdf")
def export_analytical_pdf(
    year: int = Query(default=2022, description="Reporting year"),
    state_code: str = Query(default="ALL", description="State code or 'ALL' for national"),
    metric: MetricKey = Query(default="count", description="Selected metric key"),
    compare_code: Optional[str] = Query(default=None, description="Optional secondary state code"),
    db: Session = Depends(get_db),
) -> Response:
    """Generate and download a verified, strictly 1-page A4 landscape analytical executive brief."""
    pdf_bytes = generate_single_page_pdf(
        db,
        year=year,
        state_code=state_code,
        metric=metric,
        compare_code=compare_code,
    )
    filename = f"the-unheard-brief-{year}-{state_code.lower()}-{metric}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
