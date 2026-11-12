from fastapi import APIRouter

from app.ai.engine import SUGGESTED_QUESTIONS, evaluate_ai_query
from app.schemas.dashboard import AIQueryRequest, AIQueryResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/suggestions")
def read_ai_suggestions() -> dict:
    """Return suggested investigative questions for the Phase 3 AI workspace."""
    return {
        "status": "unavailable_phase_3",
        "suggested_questions": SUGGESTED_QUESTIONS,
    }


@router.post("/query", response_model=AIQueryResponse)
def submit_ai_query(payload: AIQueryRequest) -> AIQueryResponse:
    """Return honest Phase 3 unavailability status without fabricating answers."""
    return evaluate_ai_query(payload.question)

