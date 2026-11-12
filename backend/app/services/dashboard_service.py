import csv
import io
from typing import List, Optional

from sqlalchemy.orm import Session

from app.analytics.stats import compute_yoy_series, detect_series_anomalies
from app.models.dashboard import DatasetSource, DemoNationalYear, DemoStateObservation
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    DatasetSourceSchema,
    DemographicBucket,
    GeographicAnalysisResponse,
    KPIItem,
    MethodologySectionSchema,
    MetricKey,
    NationalTrendPoint,
    ResearchPreviewRequest,
    ResearchPreviewResponse,
    SourceTransparencyBadge,
    SourcesMethodologyResponse,
    StateRecord,
    StatisticalObservation,
    TrendsPatternsResponse,
)

DEMO_BANNER = (
    "DEMO DATA — Phase 1 structural placeholders only. Do not cite or interpret as "
    "official NCRB statistics. Verified datasets will be ingested in Phase 2."
)

SEED_SOURCES = [
    {
        "slug": "ncrb-crime-in-india",
        "name": "Crime in India — Annual Statistical Compendium",
        "publisher": "National Crime Records Bureau (Ministry of Home Affairs)",
        "reporting_period": "2003–2022 (Planned Phase 2 Ingestion)",
        "status": "Awaiting Phase 2 Ingestion",
        "granularity": "National, State/UT & Metropolitan Aggregates",
        "definitions_summary": (
            "Covers police-registered FIRs under IPC Sections 375/376 (and transitioned BNS "
            "Sections 63–70), subject to the NCRB Principal Offence Rule."
        ),
        "missing_data_notes": (
            "Reflects police-recorded cases only; does not capture unreported incidents. "
            "Historical tables require cross-walking post-2013 Criminal Law Amendment definitions."
        ),
        "source_url": "https://ncrb.gov.in/",
    },
    {
        "slug": "nfhs-5-survey",
        "name": "National Family Health Survey (NFHS-4 & NFHS-5)",
        "publisher": "Ministry of Health & Family Welfare / IIPS",
        "reporting_period": "2015–16, 2019–21 (Planned Phase 2 Contextual Layer)",
        "status": "Schema Mapped",
        "granularity": "National & State/UT Household Sample",
        "definitions_summary": (
            "Probability household survey capturing self-reported prevalence and formal "
            "help-seeking behaviour among adult women."
        ),
        "missing_data_notes": (
            "Periodic survey waves rather than annual series; essential to interpret the gap "
            "between actual prevalence and formal FIR registration."
        ),
        "source_url": "https://rchiips.org/nfhs/",
    },
    {
        "slug": "census-population-projections",
        "name": "Census of India & Technical Group Population Projections",
        "publisher": "Office of the Registrar General & Census Commissioner, India",
        "reporting_period": "2001–2026 Projected Female Population",
        "status": "Denominator Reference Ready",
        "granularity": "State / UT Annual Mid-Year Female Population",
        "definitions_summary": (
            "Provides standardized female population denominators for computing per-100,000 "
            "reporting rates across differently sized states."
        ),
        "missing_data_notes": (
            "2021 decennial Census delay necessitates reliance on official MoHFW/RGI projected "
            "population tables."
        ),
        "source_url": "https://censusindia.gov.in/",
    },
    {
        "slug": "doj-ftsc-disposal",
        "name": "Fast Track Special Courts & eCourts Disposal Registry",
        "publisher": "Department of Justice, Ministry of Law & Justice",
        "reporting_period": "2019–Present (Planned Phase 2)",
        "status": "Metadata Mapped",
        "granularity": "State High Court & District Court Aggregates",
        "definitions_summary": (
            "Tracks case pendency, trial duration, and judicial disposal counts across "
            "designated special courts."
        ),
        "missing_data_notes": (
            "Annual court disposals include backlog from prior years and cannot be divided "
            "directly by same-year FIR registrations."
        ),
        "source_url": "https://doj.gov.in/",
    },
]

METHODOLOGY_DOCS = [
    {
        "id": "ncrb-reports",
        "title": "NCRB Source Reports & Institutional Scope",
        "summary": "How National Crime Records Bureau annual compendia are compiled from State Crime Records Bureaux.",
        "details": [
            "NCRB compiles police-recorded First Information Reports (FIRs) submitted by State/UT police departments.",
            "Figures reflect administrative registrations in a given calendar year, not date of incident occurrence.",
        ],
    },
    {
        "id": "reporting-periods",
        "title": "Dataset Reporting Periods & Lag",
        "summary": "Why official publication timelines lag calendar years and how waves align.",
        "details": [
            "Annual NCRB Crime in India editions are typically released 9–18 months after the close of the calendar year.",
            "Survey waves (NFHS) occur every 4–5 years and provide structural context rather than annual time-series.",
        ],
    },
    {
        "id": "definitions",
        "title": "Data Definitions & Principal Offence Rule",
        "summary": "Statutory scope under IPC Section 375/376, POCSO overlaps, and BNS transition.",
        "details": [
            "Under NCRB's Principal Offence Rule, when multiple IPC sections appear in one FIR, only the offence carrying the highest punishment is tabulated in headline counts.",
            "Charge-sheet rate measures the proportion of investigated cases sent for trial against total cases disposed by police.",
        ],
    },
    {
        "id": "missing-data",
        "title": "Missing Data & Structural Gaps",
        "summary": "Handling bifurcated states, delayed Census denominators, and non-reporting barriers.",
        "details": [
            "State boundaries changed during the 20-year window (e.g., Andhra Pradesh / Telangana in 2014; Jammu & Kashmir / Ladakh reorganization in 2019).",
            "Time-of-day, granular city-ward, or incident-level narratives are excluded unless explicitly present in verified public tables.",
        ],
    },
    {
        "id": "legal-changes",
        "title": "Legal Classification Changes (2013, 2018, 2024)",
        "summary": "Why longitudinal charts annotate statutory regime shifts.",
        "details": [
            "The Criminal Law (Amendment) Act, 2013 broadened statutory definitions and mandated strict FIR registration procedures (Section 166A IPC).",
            "The Bharatiya Nyaya Sanhita (BNS) 2023/2024 transitions IPC 375/376 into BNS Sections 63–70.",
        ],
    },
    {
        "id": "reported-vs-prevalence",
        "title": "Reported Cases vs. Actual Prevalence",
        "summary": "Why higher FIR counts do not automatically mean higher underlying violence.",
        "details": [
            "Higher reported rates in a state can reflect stronger police accessibility, survivor awareness, and willingness to file FIRs.",
            "Conversely, very low reported rates can mask severe social stigma, economic dependence, or institutional deterrence.",
        ],
    },
    {
        "id": "calculation-methodology",
        "title": "Calculation Methodology",
        "summary": "Standardized formulas used in Phase 1 and Phase 2 analytics.",
        "details": [
            "Rate per 100,000 female population = (Reported Cases / Mid-Year Projected Female Population) × 100,000.",
            "Year-on-Year (YoY) % Change = ((Current Year − Prior Year) / Prior Year) × 100.",
        ],
    },
]

# Synthetic Phase 1 placeholder series (explicitly marked DEMO DATA)
SEED_NATIONAL_TREND = [
    (2003, 15800, 3.0, 78.2, 27.1, None),
    (2004, 16900, 3.2, 78.8, 26.8, None),
    (2005, 17400, 3.2, 79.1, 26.4, None),
    (2006, 18200, 3.3, 79.5, 26.9, None),
    (2007, 19500, 3.5, 80.0, 26.2, None),
    (2008, 20100, 3.6, 80.3, 25.9, None),
    (2009, 20400, 3.6, 80.6, 26.1, None),
    (2010, 21100, 3.7, 81.1, 26.4, None),
    (2011, 22900, 3.9, 81.8, 25.8, None),
    (2012, 23800, 4.0, 82.0, 24.9, None),
    (2013, 31200, 5.2, 83.4, 27.0, "Criminal Law (Amendment) Act, 2013"),
    (2014, 34100, 5.6, 84.1, 27.6, None),
    (2015, 32900, 5.3, 83.8, 28.4, None),
    (2016, 36200, 5.8, 84.5, 26.1, None),
    (2017, 31500, 5.0, 83.9, 30.2, "NCRB counting methodology revision"),
    (2018, 32100, 5.0, 84.2, 27.8, "Criminal Law (Amendment) Act, 2018"),
    (2019, 31100, 4.8, 84.0, 28.1, None),
    (2020, 27100, 4.1, 82.5, 34.0, "Pandemic lockdowns & court closure disruption"),
    (2021, 30600, 4.6, 83.6, 28.9, None),
    (2022, 30900, 4.6, 83.9, 27.6, None),
]

# Synthetic state/UT placeholder profiles across 2018-2022 (explicitly labeled DEMO DATA)
SEED_STATE_PROFILES = [
    ("RJ", "Rajasthan", "North", 4800, 12.1, 78.4, 31.2),
    ("UP", "Uttar Pradesh", "North", 3400, 3.1, 82.6, 56.4),
    ("MP", "Madhya Pradesh", "Central", 3100, 7.5, 88.2, 32.8),
    ("MH", "Maharashtra", "West", 2750, 4.5, 85.7, 19.4),
    ("HR", "Haryana", "North", 1620, 11.4, 79.1, 24.5),
    ("AS", "Assam", "North-East", 1480, 8.6, 74.8, 17.9),
    ("OD", "Odisha", "East", 1420, 6.2, 86.1, 14.3),
    ("DL", "Delhi (NCT)", "North", 1210, 12.6, 81.9, 26.2),
    ("KA", "Karnataka", "South", 610, 1.8, 89.4, 21.7),
    ("WB", "West Bengal", "East", 1090, 2.2, 84.2, 13.8),
    ("BR", "Bihar", "East", 860, 1.5, 80.5, 29.4),
    ("KL", "Kerala", "South", 780, 4.2, 91.2, 23.6),
    ("GJ", "Gujarat", "West", 590, 1.8, 90.4, 18.2),
    ("TN", "Tamil Nadu", "South", 430, 1.1, 88.9, 27.5),
    ("PB", "Punjab", "North", 510, 3.5, 83.7, 25.1),
]

YEAR_MULTIPLIERS = {
    2018: 1.02,
    2019: 1.00,
    2020: 0.87,
    2021: 0.98,
    2022: 1.00,
}

DEMO_RELATIONSHIP_BUCKETS = [
    DemographicBucket(
        category="Known Persons (Acquaintances / Neighbours / Employers)",
        share_pct=68.4,
        note="DEMO DATA placeholder mirroring standard NCRB offender-relationship grouping.",
    ),
    DemographicBucket(
        category="Family Members & Close Relatives",
        share_pct=11.2,
        note="DEMO DATA placeholder illustrating domestic reporting category slot.",
    ),
    DemographicBucket(
        category="Online / Pretext / Other Known Contacts",
        share_pct=13.6,
        note="DEMO DATA placeholder for post-2017 NCRB sub-classifications.",
    ),
    DemographicBucket(
        category="Unknown / Unidentified Offenders",
        share_pct=6.8,
        note="DEMO DATA placeholder representing stranger-reported cases.",
    ),
]

DEMO_AGE_BUCKETS = [
    DemographicBucket(
        category="18–30 Years",
        share_pct=47.5,
        note="DEMO DATA placeholder aligned with adult NCRB age-bracket tables.",
    ),
    DemographicBucket(
        category="Below 18 Years (Including POCSO Cross-Tabs)",
        share_pct=31.2,
        note="DEMO DATA placeholder noting statutory overlap with POCSO Act tables.",
    ),
    DemographicBucket(
        category="30–45 Years",
        share_pct=17.4,
        note="DEMO DATA placeholder aligned with NCRB age-bracket tables.",
    ),
    DemographicBucket(
        category="45+ Years",
        share_pct=3.9,
        note="DEMO DATA placeholder aligned with NCRB age-bracket tables.",
    ),
]


def ensure_seed_data(db: Session) -> None:
    """Seed SQLite with source metadata and explicitly flagged DEMO DATA placeholders."""
    if db.query(DatasetSource).count() == 0:
        for src in SEED_SOURCES:
            db.add(DatasetSource(**src))

    if db.query(DemoNationalYear).count() == 0:
        for yr, cases, rate, cs_pct, conv_pct, note in SEED_NATIONAL_TREND:
            db.add(
                DemoNationalYear(
                    year=yr,
                    demo_reported_cases=cases,
                    demo_rate_per_100k=rate,
                    demo_charge_sheet_pct=cs_pct,
                    demo_conviction_pct=conv_pct,
                    statutory_note=note,
                    is_demo=True,
                )
            )

    if db.query(DemoStateObservation).count() == 0:
        for idx, (code, name, zone, base_cases, base_rate, base_cs, base_conv) in enumerate(
            SEED_STATE_PROFILES
        ):
            for yr, mult in YEAR_MULTIPLIERS.items():
                # Slight deterministic per-state variation by year so YoY rankings shift realistically
                offset = ((idx % 5) - 2) * (yr - 2020) * 0.012
                factor = max(0.75, mult + offset)
                db.add(
                    DemoStateObservation(
                        state_code=code,
                        state_name=name,
                        region_zone=zone,
                        year=yr,
                        demo_reported_cases=int(round(base_cases * factor)),
                        demo_rate_per_100k=round(base_rate * factor, 2),
                        demo_charge_sheet_pct=round(min(97.0, base_cs + (yr - 2020) * 0.4), 1),
                        demo_conviction_pct=round(max(10.0, base_conv + (2020 - yr) * 0.3), 1),
                        is_demo=True,
                    )
                )

    db.commit()


def _metric_sort_value(row: DemoStateObservation, metric: MetricKey) -> float:
    if metric == "rate_per_100k":
        return row.demo_rate_per_100k
    if metric == "charge_sheet_pct":
        return row.demo_charge_sheet_pct
    if metric == "conviction_pct":
        return row.demo_conviction_pct
    return float(row.demo_reported_cases)


def _to_state_records(
    rows: List[DemoStateObservation], metric: MetricKey
) -> List[StateRecord]:
    ordered = sorted(rows, key=lambda r: _metric_sort_value(r, metric), reverse=True)
    return [
        StateRecord(
            state_code=r.state_code,
            state_name=r.state_name,
            region_zone=r.region_zone,
            year=r.year,
            demo_reported_cases=r.demo_reported_cases,
            demo_rate_per_100k=r.demo_rate_per_100k,
            demo_charge_sheet_pct=r.demo_charge_sheet_pct,
            demo_conviction_pct=r.demo_conviction_pct,
            rank_by_selected=idx + 1,
            is_demo=True,
        )
        for idx, r in enumerate(ordered)
    ]


def _get_national_trend_points(db: Session) -> List[NationalTrendPoint]:
    rows = db.query(DemoNationalYear).order_by(DemoNationalYear.year.asc()).all()
    raw = [
        {
            "year": r.year,
            "demo_reported_cases": r.demo_reported_cases,
            "demo_rate_per_100k": r.demo_rate_per_100k,
            "demo_charge_sheet_pct": r.demo_charge_sheet_pct,
            "demo_conviction_pct": r.demo_conviction_pct,
            "statutory_note": r.statutory_note,
            "is_demo": True,
        }
        for r in rows
    ]
    enriched = compute_yoy_series(raw)
    return [NationalTrendPoint(**pt) for pt in enriched]


def get_overview(
    db: Session, year: Optional[int] = None, metric: MetricKey = "count"
) -> DashboardOverviewResponse:
    """Build Overview payload for the selected year and metric."""
    ensure_seed_data(db)

    state_years = sorted(
        {r[0] for r in db.query(DemoStateObservation.year).distinct().all()}
    )
    selected_year = year if year in state_years else state_years[-1]

    national_points = _get_national_trend_points(db)
    current_pt = next((p for p in national_points if p.year == selected_year), national_points[-1])

    state_rows = (
        db.query(DemoStateObservation)
        .filter(DemoStateObservation.year == selected_year)
        .all()
    )
    ranked_states = _to_state_records(state_rows, metric)

    yoy = current_pt.yoy_change_pct
    yoy_display = f"{yoy:+.1f}%" if yoy is not None else "N/A"
    yoy_dir = "up" if (yoy or 0) > 0 else ("down" if (yoy or 0) < 0 else "neutral")

    kpis = [
        KPIItem(
            id="kpi-reported",
            label="Total Reported Cases",
            value=f"{current_pt.demo_reported_cases:,}",
            delta_label=f"Rate {current_pt.demo_rate_per_100k:.1f} / 100k (DEMO)",
            delta_direction="neutral",
            footnote=f"DEMO DATA placeholder for reporting year {selected_year}.",
            is_demo=True,
        ),
        KPIItem(
            id="kpi-yoy",
            label="Year-on-Year Change",
            value=yoy_display,
            delta_label=f"vs. {selected_year - 1} baseline",
            delta_direction=yoy_dir,
            footnote="DEMO DATA: Computed by Pandas YoY pipeline on synthetic placeholder series.",
            is_demo=True,
        ),
        KPIItem(
            id="kpi-coverage",
            label="States / UTs Covered",
            value=f"{len(ranked_states)} / 36",
            delta_label="Phase 1 Sample Schema",
            delta_direction="neutral",
            footnote="15 representative demo profiles active; full 36 States/UTs arrive in Phase 2.",
            is_demo=True,
        ),
        KPIItem(
            id="kpi-latest-year",
            label="Latest Reporting Year",
            value=str(state_years[-1]),
            delta_label=f"Viewing {selected_year}",
            delta_direction="neutral",
            footnote="Awaiting official NCRB Crime in India release ingestion (Phase 2).",
            is_demo=True,
        ),
    ]

    insights = [
        StatisticalObservation(
            id="obs-phase3-slot-1",
            title="Statutory Breakpoint Sensitivity (2013)",
            category="Phase 3 Insight Slot · DEMO DATA",
            summary=(
                "DEMO DATA: Longitudinal models must segment pre-2013 and post-2013 series to "
                "separate statutory expansion effects from underlying incidence shifts."
            ),
            is_demo=True,
        ),
        StatisticalObservation(
            id="obs-phase3-slot-2",
            title="Count vs. Population Rate Divergence",
            category="Phase 3 Insight Slot · DEMO DATA",
            summary=(
                "DEMO DATA: High-population states lead absolute case counts while smaller states "
                "and UTs can rank higher under per-100,000 female population normalization."
            ),
            is_demo=True,
        ),
        StatisticalObservation(
            id="obs-phase3-slot-3",
            title="Automated Observation Engine Reserved",
            category="Phase 3 Architecture",
            summary=(
                "In Phase 3, this panel will surface statistical observations verified directly "
                "against ingested NCRB, NFHS, and judicial disposal tables."
            ),
            is_demo=True,
        ),
    ]

    return DashboardOverviewResponse(
        is_demo=True,
        demo_banner=DEMO_BANNER,
        selected_year=selected_year,
        available_years=state_years,
        selected_metric=metric,
        kpis=kpis,
        national_trend=national_points,
        top_states=ranked_states[:10],
        research_insights=insights,
        source_transparency=SourceTransparencyBadge(
            dataset_name="Phase 1 Synthetic Schema (Target: NCRB Crime in India + NFHS-5)",
            reporting_period="2003–2022 (National Demo) · 2018–2022 (State Demo)",
            source_status="DEMO DATA ACTIVE · Phase 2 Ingestion Pending",
            phase_notice=(
                "All numeric indicators displayed in Phase 1 are structural placeholders. "
                "Official NCRB tables are not yet ingested."
            ),
        ),
    )


def get_geographic_analysis(
    db: Session,
    year: Optional[int] = None,
    metric: MetricKey = "rate_per_100k",
    region: str = "ALL",
    search: str = "",
) -> GeographicAnalysisResponse:
    """Build Geographic Analysis workspace payload."""
    ensure_seed_data(db)

    state_years = sorted(
        {r[0] for r in db.query(DemoStateObservation.year).distinct().all()}
    )
    selected_year = year if year in state_years else state_years[-1]

    query = db.query(DemoStateObservation).filter(DemoStateObservation.year == selected_year)
    if region and region != "ALL":
        query = query.filter(DemoStateObservation.region_zone == region)
    if search.strip():
        pattern = f"%{search.strip()}%"
        query = query.filter(DemoStateObservation.state_name.ilike(pattern))

    rows = query.all()
    all_regions = sorted(
        {r[0] for r in db.query(DemoStateObservation.region_zone).distinct().all()}
    )

    return GeographicAnalysisResponse(
        is_demo=True,
        demo_banner=DEMO_BANNER,
        selected_year=selected_year,
        available_years=state_years,
        selected_metric=metric,
        regions=all_regions,
        states=_to_state_records(rows, metric),
        map_architecture_status=(
            "Phase 2 GeoJSON Ready — Placeholder spatial layer active. Official Indian state "
            "and UT polygon boundaries will be connected in Phase 2."
        ),
    )


def get_trends_patterns(
    db: Session, start_year: Optional[int] = None, end_year: Optional[int] = None
) -> TrendsPatternsResponse:
    """Build Trends & Patterns workspace payload."""
    ensure_seed_data(db)

    full_series = _get_national_trend_points(db)
    available_years = [p.year for p in full_series]
    s_year = start_year if start_year in available_years else available_years[0]
    e_year = end_year if end_year in available_years else available_years[-1]
    if s_year > e_year:
        s_year, e_year = e_year, s_year

    filtered = [p for p in full_series if s_year <= p.year <= e_year]
    anomalies_raw = detect_series_anomalies([p.model_dump() for p in filtered])
    anomalies = [StatisticalObservation(**a) for a in anomalies_raw]

    return TrendsPatternsResponse(
        is_demo=True,
        demo_banner=DEMO_BANNER,
        start_year=s_year,
        end_year=e_year,
        available_years=available_years,
        series=filtered,
        offender_relationship_demo=DEMO_RELATIONSHIP_BUCKETS,
        age_group_demo=DEMO_AGE_BUCKETS,
        anomalies=anomalies,
    )


def build_research_preview(
    db: Session, payload: ResearchPreviewRequest
) -> ResearchPreviewResponse:
    """Filter demo observations for Research & Export and generate stamped CSV text."""
    ensure_seed_data(db)

    state_years = sorted(
        {r[0] for r in db.query(DemoStateObservation.year).distinct().all()}
    )
    valid_years = [y for y in payload.years if y in state_years] or [state_years[-1]]

    query = db.query(DemoStateObservation).filter(DemoStateObservation.year.in_(valid_years))
    if payload.state_codes:
        query = query.filter(DemoStateObservation.state_code.in_(payload.state_codes))

    rows = query.order_by(DemoStateObservation.year.asc(), DemoStateObservation.state_name.asc()).all()
    records = _to_state_records(rows, payload.metric)

    buf = io.StringIO()
    buf.write("# THE UNHEARD — DEMO DATA EXPORT (NOT OFFICIAL NCRB STATISTICS)\n")
    writer = csv.writer(buf)
    writer.writerow(
        [
            "state_code",
            "state_name",
            "region_zone",
            "year",
            "demo_reported_cases",
            "demo_rate_per_100k",
            "demo_charge_sheet_pct",
            "demo_conviction_pct",
            "is_demo",
        ]
    )
    for rec in records:
        writer.writerow(
            [
                rec.state_code,
                rec.state_name,
                rec.region_zone,
                rec.year,
                rec.demo_reported_cases,
                rec.demo_rate_per_100k,
                rec.demo_charge_sheet_pct,
                rec.demo_conviction_pct,
                "DEMO_DATA",
            ]
        )

    return ResearchPreviewResponse(
        is_demo=True,
        demo_banner=DEMO_BANNER,
        metric=payload.metric,
        years=sorted(valid_years),
        state_codes=payload.state_codes,
        rows=records,
        csv_preview=buf.getvalue(),
    )


def get_sources_methodology(db: Session) -> SourcesMethodologyResponse:
    """Return tracked source registries and methodology documentation."""
    ensure_seed_data(db)
    rows = db.query(DatasetSource).order_by(DatasetSource.id.asc()).all()
    datasets = [
        DatasetSourceSchema(
            slug=r.slug,
            name=r.name,
            publisher=r.publisher,
            reporting_period=r.reporting_period,
            status=r.status,
            granularity=r.granularity,
            definitions_summary=r.definitions_summary,
            missing_data_notes=r.missing_data_notes,
            source_url=r.source_url,
        )
        for r in rows
    ]
    return SourcesMethodologyResponse(
        datasets=datasets,
        methodology_sections=[MethodologySectionSchema(**sec) for sec in METHODOLOGY_DOCS],
    )

