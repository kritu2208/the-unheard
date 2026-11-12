from app.schemas.dashboard import AIQueryResponse

SUGGESTED_QUESTIONS = [
    "How did the Criminal Law (Amendment) Act, 2013 alter statutory reporting categories?",
    "Compare reported FIR rates per 100,000 female population vs. raw case counts across states.",
    "Why do police-recorded NCRB tables differ from NFHS household survey help-seeking indicators?",
    "What explains judicial pendency and conviction lag across multi-year court disposal tables?",
]


def evaluate_ai_query(question: str) -> AIQueryResponse:
    """
    Phase 1 contract for AI Intelligence.

    Refuses to fabricate statistical answers or synthetic citations before
    Phase 2 official dataset ingestion and Phase 3 grounded retrieval are enabled.
    """
    return AIQueryResponse(
        status="unavailable_phase_3",
        answered=False,
        question=question.strip(),
        message=(
            "AI Intelligence is scheduled for Phase 3. Because THE UNHEARD prohibits "
            "ungrounded statistical generation, natural-language answers remain disabled "
            "until verified NCRB tables, population denominators, and statutory codebooks "
            "are ingested in Phase 2."
        ),
        suggested_questions=SUGGESTED_QUESTIONS,
        citation_requirements=[
            "Verified NCRB Crime in India annual table row references (Phase 2)",
            "Census / projected female population denominator alignment (Phase 2)",
            "Statutory footnote & Principal Offence Rule retrieval index (Phase 3)",
        ],
    )

