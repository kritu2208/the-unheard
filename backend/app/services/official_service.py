import csv
import io
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.analytics.stats import compute_yoy_series, detect_series_anomalies
from app.ingestion.pipeline import run_registered_ingestion
from app.models.records import (
    CrimeStatistic,
    DataQualityIssue,
    DataSource,
    Dataset,
    DatasetVersion,
    GeographicUnit,
    PopulationStatistic,
)
from app.schemas.dashboard import (
    DashboardInsightsResponse,
    DashboardOverviewResponse,
    DataQualityIssueSchema,
    DataQualityReportResponse,
    DatasetListResponse,
    DatasetSourceSchema,
    DatasetVersionDetailSchema,
    DemographicBucket,
    DeterministicInsight,
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

OFFICIAL_DATA_BANNER = (
    "VERIFIED OFFICIAL DATA — Sourced directly from National Crime Records Bureau (NCRB) "
    "Crime in India publications (2018–2023). Figures reflect police-registered FIRs under "
    "the Principal Offence Rule, not actual societal prevalence."
)

BOUNDARY_STATUTORY_NOTES = {
    2018: "Pre-2019 undivided Jammu & Kashmir reporting; Total CAW only (Sec. 376 state tables not ingested for 2018).",
    2019: "Jammu & Kashmir reorganized into J&K and Ladakh UTs (Oct 2019); Total CAW only.",
    2020: "Full Chapter 3A Sec. 376 Rape ingested; DNH & DD merged (Jan 2020); COVID-19 mobility restrictions affected reporting.",
    2021: "Full Chapter 3A Sec. 376 Rape ingested (Tables 3A.1–3A.11).",
    2022: "Latest complete State/UT Chapter 3A Sec. 376 Rape release from NCRB.",
    2023: "Official National Total CAW (448,211) from NCRB 9-2023.pdf; granular State/UT Sec. 376 Excel tables unavailable from NCRB.",
}

METHODOLOGY_SECTIONS = [
    {
        "id": "units-and-principal-offence",
        "title": "Official Statistical Units & Principal Offence Rule",
        "summary": (
            "NCRB statistics measure police-registered First Information Reports (FIRs), "
            "not societal incidence or prevalence."
        ),
        "details": [
            "Cases Registered (I) and Female Victims (V) are recorded separately in NCRB Table 3A.2 and never merged.",
            "Under NCRB's Principal Offence Rule, a single FIR with multiple criminal sections is counted only once under the offence carrying the highest penalty.",
            "Rape (Sec. 376 IPC) counts are strictly separated from Attempt to Rape (Sec. 376/511), POCSO Child Rape (Sec. 4 & 6), Murder with Rape, and Total Crime Against Women (IPC+SLL).",
        ],
    },
    {
        "id": "population-denominators",
        "title": "Population Denominators & Rate Formulas",
        "summary": "Rates per lakh female population use official RGI/MoHFW mid-year female projections.",
        "details": [
            "Formula: Rate per 100,000 female population = Registered Cases / Projected Mid-Year Female Population (in Lakhs).",
            "Female projections are extracted directly from NCRB Table 3A.1 (2020–2022 editions). NCRB 2023 Prelims p.viii (6Population2023.pdf) publishes Total Population (both sexes), which is tagged 'total' and excluded from female crime-rate calculations.",
            "No rates are fabricated or interpolated when an official matching female denominator is unavailable.",
        ],
    },
    {
        "id": "disposal-boundaries",
        "title": "Police & Court Disposal Boundaries (National vs. State/UT)",
        "summary": "Sec. 376 Rape disposal rates are published nationally; State tables aggregate all Crimes Against Women.",
        "details": [
            "All-India Sec. 376 Rape chargesheeting rates (Table 3A.5: Cases Chargesheeted / Total Cases Disposed by Police * 100) and conviction rates (Table 3A.7: Cases Convicted / Trials Completed * 100) are exact official figures for 2020–2022.",
            "Tables 3A.6 and 3A.8 report State/UT disposal ONLY for Total Crime Against Women (IPC+SLL) across all crime heads, NOT Rape alone. State-level Sec. 376 disposal is therefore surfaced as Unavailable rather than substituted.",
        ],
    },
    {
        "id": "legal-and-boundary-shifts",
        "title": "Statutory & Administrative Breakpoints (2013, 2019–2020, 2024)",
        "summary": "Changes in Indian criminal law and UT boundaries require longitudinal caveats.",
        "details": [
            "Criminal Law (Amendment) Act, 2013 broadened IPC Sec. 375/376 definitions post-April 2013.",
            "Jammu & Kashmir & Ladakh reorganized (31 Oct 2019); Dadra & Nagar Haveli & Daman & Diu merged (26 Jan 2020).",
            "Bharatiya Nyaya Sanhita (BNS 2023, Sec. 63–71) replaced IPC Sec. 376 effective 1 July 2024.",
        ],
    },
]


def ensure_official_data(db: Session) -> None:
    """Ingest registered official NCRB datasets on first startup if database tables are empty."""
    existing_count = db.scalar(select(func.count(CrimeStatistic.id))) or 0
    if existing_count == 0:
        run_registered_ingestion(db, force=False)


def _select_authoritative_map(rows: List[Tuple]) -> Dict[Tuple[int, str, str], Tuple[float, str, str]]:
    """Collapse overlapping multi-edition rows (e.g. Table 3A.1 2020 CAW in 2020/2021/2022) preferring latest edition."""
    best: Dict[Tuple[int, str, str], Tuple[float, str, str]] = {}
    for year, geo_code, metric_type, val, source_table, val_status in rows:
        key = (int(year), str(geo_code), str(metric_type))
        prev = best.get(key)
        # Prefer latest edition year lexicographically ("TABLE 3A.2 (2022..." > "TABLE 3A.1 (2022..." > "TABLE 3A.1 (2020...")
        if prev is None or source_table > prev[1]:
            best[key] = (float(val) if val is not None else 0.0, str(source_table), str(val_status))
    return best


def _get_year_sets(db: Session) -> Tuple[List[int], List[int]]:
    """Return (all_available_years, granular_rape_years)."""
    all_yrs = list(
        db.scalars(
            select(CrimeStatistic.reporting_year).distinct().order_by(CrimeStatistic.reporting_year)
        ).all()
    )
    rape_yrs = list(
        db.scalars(
            select(CrimeStatistic.reporting_year)
            .where(CrimeStatistic.crime_domain == "rape_ipc_376", CrimeStatistic.sub_category == "Total")
            .distinct()
            .order_by(CrimeStatistic.reporting_year)
        ).all()
    )
    return sorted(all_yrs), sorted(rape_yrs)


def _get_national_series(db: Session) -> List[Dict]:
    """Assemble clean All-India longitudinal series keeping Sec. 376 Rape & CAW separated."""
    in_geo = db.scalar(select(GeographicUnit).where(GeographicUnit.code == "IN"))
    if in_geo is None:
        return []

    rows = db.execute(
        select(
            CrimeStatistic.reporting_year,
            CrimeStatistic.crime_domain,
            CrimeStatistic.metric_type,
            CrimeStatistic.normalized_value,
            CrimeStatistic.source_table,
        ).where(
            CrimeStatistic.geographic_unit_id == in_geo.id,
            CrimeStatistic.sub_category == "Total",
            CrimeStatistic.crime_domain.in_(
                [
                    "rape_ipc_376",
                    "caw_total",
                    "rape_national_police_disposal",
                    "rape_national_court_disposal",
                ]
            ),
            CrimeStatistic.crime_head.in_(
                ["Rape (Sec. 376 IPC)", "Total Crime against Women (IPC+SLL)"]
            ),
            CrimeStatistic.normalized_value.is_not(None),
        )
    ).all()

    by_year: Dict[int, Dict] = {}
    for yr, domain, mtype, val, src_tbl in rows:
        bucket = by_year.setdefault(
            int(yr),
            {
                "year": int(yr),
                "rape_cases_available": False,
                "reported_cases": None,
                "victims_count": None,
                "rate_per_100k_female": None,
                "charge_sheet_pct": None,
                "conviction_pct": None,
                "trial_pendency_pct": None,
                "caw_total_cases": None,
                "caw_rate_per_100k_female": None,
                "statutory_note": BOUNDARY_STATUTORY_NOTES.get(int(yr)),
                "source_table": src_tbl,
            },
        )
        if domain == "rape_ipc_376":
            bucket["rape_cases_available"] = True
            bucket["source_table"] = src_tbl
            if mtype == "cases_registered":
                bucket["reported_cases"] = int(round(val))
            elif mtype == "victims":
                bucket["victims_count"] = int(round(val))
            elif mtype == "rate_per_100k_female":
                bucket["rate_per_100k_female"] = round(float(val), 2)
        elif domain == "rape_national_police_disposal" and mtype == "chargesheet_rate_pct":
            bucket["charge_sheet_pct"] = round(float(val), 2)
        elif domain == "rape_national_court_disposal":
            if mtype == "conviction_rate_pct":
                bucket["conviction_pct"] = round(float(val), 2)
            elif mtype == "trial_pendency_pct":
                bucket["trial_pendency_pct"] = round(float(val), 2)
        elif domain == "caw_total":
            if mtype == "cases_registered":
                # Keep authoritative latest edition for multi-year CAW
                if bucket["caw_total_cases"] is None or "2022" in src_tbl or "2023" in src_tbl:
                    bucket["caw_total_cases"] = int(round(val))
                    if not bucket["rape_cases_available"]:
                        bucket["source_table"] = src_tbl
            elif mtype == "rate_per_100k_female":
                bucket["caw_rate_per_100k_female"] = round(float(val), 2)

    sorted_rows = [by_year[y] for y in sorted(by_year.keys())]
    return compute_yoy_series(sorted_rows)


def _fetch_state_records(
    db: Session,
    years: List[int],
    metric: MetricKey,
    region: str = "ALL",
    search: str = "",
    state_codes: Optional[List[str]] = None,
) -> Tuple[List[StateRecord], bool, Optional[str]]:
    """Build ranked State/UT records from verified DB tables with strict unavailability semantics."""
    # Check state-level metric availability honesty
    if metric in {"charge_sheet_pct", "conviction_pct"}:
        reason = (
            "NCRB publishes Rape (Sec. 376 IPC) police chargesheeting and court conviction rates only "
            "at the All-India crime-head level (Tables 3A.5 & 3A.7). State/UT tables 3A.6 & 3A.8 aggregate "
            "all Crimes Against Women (IPC+SLL) combined and cannot be substituted for Sec. 376 Rape."
        )
        metric_available = False
    else:
        reason = None
        metric_available = True

    stmt = (
        select(
            CrimeStatistic.reporting_year,
            GeographicUnit.code,
            GeographicUnit.canonical_name,
            GeographicUnit.unit_type,
            GeographicUnit.region_zone,
            GeographicUnit.boundary_notes,
            CrimeStatistic.crime_domain,
            CrimeStatistic.metric_type,
            CrimeStatistic.normalized_value,
            CrimeStatistic.source_table,
            CrimeStatistic.validation_status,
            CrimeStatistic.validation_notes,
        )
        .join(GeographicUnit, CrimeStatistic.geographic_unit_id == GeographicUnit.id)
        .where(
            GeographicUnit.unit_type.in_(["state", "union_territory"]),
            CrimeStatistic.reporting_year.in_(years),
            CrimeStatistic.sub_category.in_(["Total", "Total CAW (Not Rape-only)"]),
            CrimeStatistic.crime_domain.in_(
                ["rape_ipc_376", "caw_total", "caw_state_police_disposal", "caw_state_court_disposal"]
            ),
        )
    )
    if region != "ALL":
        stmt = stmt.where(GeographicUnit.region_zone == region)
    if state_codes:
        stmt = stmt.where(GeographicUnit.code.in_([c.upper() for c in state_codes]))
    if search.strip():
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            GeographicUnit.canonical_name.ilike(like) | GeographicUnit.code.ilike(like)
        )

    raw_rows = db.execute(stmt).all()

    # Load matched female projected population (in Lakhs) per (year, geo_code)
    pop_rows = db.execute(
        select(
            PopulationStatistic.reporting_year,
            GeographicUnit.code,
            PopulationStatistic.population_lakhs,
        )
        .join(GeographicUnit, PopulationStatistic.geographic_unit_id == GeographicUnit.id)
        .where(
            PopulationStatistic.reporting_year.in_(years),
            PopulationStatistic.denominator_scope == "female",
        )
    ).all()
    female_pop_map = {(int(yr), str(code)): float(pop) for yr, code, pop in pop_rows}

    records_map: Dict[Tuple[int, str], Dict] = {}
    for (
        yr,
        code,
        name,
        utype,
        zone,
        geo_bnote,
        domain,
        mtype,
        val,
        src_tbl,
        val_status,
        val_notes,
    ) in raw_rows:
        key = (int(yr), str(code))
        entry = records_map.setdefault(
            key,
            {
                "state_code": code,
                "state_name": name,
                "unit_type": utype,
                "region_zone": zone,
                "year": int(yr),
                "reported_cases": None,
                "victims_count": None,
                "rate_per_100k_female": None,
                "female_population_lakhs": female_pop_map.get(key),
                "caw_total_cases": None,
                "caw_charge_sheet_pct": None,
                "caw_conviction_pct": None,
                "charge_sheet_pct": None,
                "conviction_pct": None,
                "metric_available": metric_available,
                "unavailable_reason": reason,
                "validation_status": val_status,
                "source_table": src_tbl,
                "boundary_note": (val_notes or geo_bnote or None),
            },
        )
        if val is None:
            if val_status != "verified":
                entry["validation_status"] = val_status
            continue
        if domain == "rape_ipc_376":
            entry["source_table"] = src_tbl
            if mtype == "cases_registered":
                entry["reported_cases"] = int(round(val))
            elif mtype == "victims":
                entry["victims_count"] = int(round(val))
            elif mtype == "rate_per_100k_female":
                entry["rate_per_100k_female"] = round(float(val), 2)
        elif domain == "caw_total" and mtype == "cases_registered":
            if entry["caw_total_cases"] is None or "2022" in src_tbl:
                entry["caw_total_cases"] = int(round(val))
        elif domain == "caw_total" and mtype == "chargesheet_rate_pct" and entry["caw_charge_sheet_pct"] is None:
            entry["caw_charge_sheet_pct"] = round(float(val), 2)
        elif domain == "caw_state_police_disposal" and mtype == "chargesheet_rate_pct":
            entry["caw_charge_sheet_pct"] = round(float(val), 2)
        elif domain == "caw_state_court_disposal" and mtype == "conviction_rate_pct":
            entry["caw_conviction_pct"] = round(float(val), 2)

    built = []
    for entry in records_map.values():
        if entry["year"] not in {2020, 2021, 2022} and entry["reported_cases"] is None:
            entry["metric_available"] = False
            entry["unavailable_reason"] = (
                f"Granular State/UT Sec. 376 Rape Excel tables for {entry['year']} are unavailable in NCRB downloads; "
                "only Total Crime Against Women is shown where published."
            )
        built.append(StateRecord(**entry))

    def _sort_val(item: StateRecord) -> float:
        if metric == "count":
            return float(item.reported_cases if item.reported_cases is not None else -1)
        if metric == "victims":
            return float(item.victims_count if item.victims_count is not None else -1)
        if metric == "rate_per_100k":
            return float(item.rate_per_100k_female if item.rate_per_100k_female is not None else -1)
        return float(item.reported_cases if item.reported_cases is not None else -1)

    built.sort(key=lambda r: (r.year, _sort_val(r)), reverse=True)
    # Assign rank within single-year selection when metric is available
    per_year_rank: Dict[int, int] = defaultdict(int)
    for row in built:
        if metric_available and row.reported_cases is not None:
            per_year_rank[row.year] += 1
            row.rank_by_selected = per_year_rank[row.year]

    return built, metric_available, reason


def get_overview(
    db: Session,
    year: Optional[int] = None,
    metric: MetricKey = "count",
) -> DashboardOverviewResponse:
    ensure_official_data(db)
    all_years, rape_years = _get_year_sets(db)
    latest_granular = rape_years[-1] if rape_years else 2022
    latest_pub = all_years[-1] if all_years else 2023
    target_year = year if year in all_years else latest_granular

    national_raw = _get_national_series(db)
    trend_points = [NationalTrendPoint(**row) for row in national_raw]
    current_pt = next((p for p in trend_points if p.year == target_year), None)

    state_rows, metric_available, metric_reason = _fetch_state_records(db, [target_year], metric)
    top_states = [r for r in state_rows if r.reported_cases is not None][:10]

    states_covered = sum(1 for r in state_rows if r.unit_type == "state" and (r.reported_cases is not None or r.caw_total_cases is not None))
    uts_covered = sum(1 for r in state_rows if r.unit_type == "union_territory" and (r.reported_cases is not None or r.caw_total_cases is not None))

    rape_ok = bool(current_pt and current_pt.rape_cases_available and current_pt.reported_cases is not None)
    unavail_msg = (
        f"NCRB has not published State/UT or National Sec. 376 Rape Table 3A.2 spreadsheets for {target_year}. "
        f"Latest complete Rape dataset is {latest_granular}."
    )

    kpis = [
        KPIItem(
            id="reported_cases",
            label="Reported Rape Cases (Sec. 376 IPC)",
            value=f"{current_pt.reported_cases:,}" if rape_ok else "Unavailable",
            available=rape_ok,
            unavailable_reason=None if rape_ok else unavail_msg,
            delta_label=(
                f"{current_pt.yoy_change_pct:+.1f}% vs {target_year - 1}"
                if rape_ok and current_pt and current_pt.yoy_change_pct is not None
                else (
                    f"{current_pt.victims_count:,} female victims"
                    if rape_ok and current_pt and current_pt.victims_count is not None
                    else "Official granular release pending"
                )
            ),
            delta_direction=(
                "up"
                if rape_ok and current_pt and current_pt.yoy_change_pct is not None and current_pt.yoy_change_pct > 0
                else "down"
                if rape_ok and current_pt and current_pt.yoy_change_pct is not None and current_pt.yoy_change_pct < 0
                else "neutral"
            ),
            unit="Registered FIRs (Principal Offence Rule)",
            source_table=current_pt.source_table if current_pt else "NCRB TABLE 3A.2",
            footnote=f"Registered cases (I) in {target_year}; distinct from actual incidence.",
        ),
        KPIItem(
            id="female_victims_and_rate",
            label="Female Victims & Rate per 100k Female Pop.",
            value=(
                f"{current_pt.victims_count:,} · {current_pt.rate_per_100k_female:.1f}"
                if rape_ok and current_pt and current_pt.victims_count is not None and current_pt.rate_per_100k_female is not None
                else "Unavailable"
            ),
            available=rape_ok,
            unavailable_reason=None if rape_ok else unavail_msg,
            delta_label="RGI Projected Female Denominator" if rape_ok else None,
            delta_direction="neutral",
            unit="Victims (V) & Rate (R)",
            source_table="NCRB TABLE 3A.2 & 3A.1",
            footnote="A single FIR can involve multiple female victims (V >= I).",
        ),
        KPIItem(
            id="caw_context",
            label="Total Crime Against Women (IPC+SLL)",
            value=(
                f"{current_pt.caw_total_cases:,}"
                if current_pt and current_pt.caw_total_cases is not None
                else "Unavailable"
            ),
            available=bool(current_pt and current_pt.caw_total_cases is not None),
            delta_label=(
                f"{current_pt.caw_yoy_change_pct:+.1f}% vs {target_year - 1}"
                if current_pt and current_pt.caw_yoy_change_pct is not None
                else None
            ),
            delta_direction=(
                "up"
                if current_pt and current_pt.caw_yoy_change_pct and current_pt.caw_yoy_change_pct > 0
                else "down"
                if current_pt and current_pt.caw_yoy_change_pct and current_pt.caw_yoy_change_pct < 0
                else "neutral"
            ),
            unit="Broader CAW FIRs (All Heads Combined)",
            source_table="NCRB TABLE 3A.1 / 9-2023.pdf",
            footnote="Separately tracked broader category; never conflated with Sec. 376 Rape.",
        ),
        KPIItem(
            id="national_disposal",
            label="National Rape Chargesheet / Conviction",
            value=(
                f"{current_pt.charge_sheet_pct:.1f}% / {current_pt.conviction_pct:.1f}%"
                if current_pt and current_pt.charge_sheet_pct is not None and current_pt.conviction_pct is not None
                else "Unavailable"
            ),
            available=bool(current_pt and current_pt.charge_sheet_pct is not None),
            unavailable_reason=None if (current_pt and current_pt.charge_sheet_pct is not None) else unavail_msg,
            delta_label=(
                f"{current_pt.trial_pendency_pct:.1f}% court pendency"
                if current_pt and current_pt.trial_pendency_pct is not None
                else None
            ),
            delta_direction="neutral",
            unit="National Crime-Head Disposal (%)",
            source_table="NCRB TABLE 3A.5 & 3A.7",
            footnote=f"Coverage: {states_covered} States + {uts_covered} UTs ({target_year}).",
        ),
    ]

    insights: List[StatisticalObservation] = []
    if rape_ok and current_pt and current_pt.reported_cases and current_pt.victims_count:
        excess_v = current_pt.victims_count - current_pt.reported_cases
        insights.append(
            StatisticalObservation(
                id="cases-vs-victims",
                title=f"Cases vs. Victims Separation ({target_year})",
                category="Official NCRB Integrity",
                summary=(
                    f"NCRB recorded {current_pt.reported_cases:,} Sec. 376 FIRs involving {current_pt.victims_count:,} "
                    f"female victims (+{excess_v:,} multi-victim cases), corresponding to {current_pt.rate_per_100k_female:.1f} "
                    "cases per 100,000 projected female population."
                ),
                source_table="NCRB TABLE 3A.2",
            )
        )
    # Known offender share from Table 3A.4
    known_share = db.scalar(
        select(CrimeStatistic.normalized_value)
        .join(GeographicUnit, CrimeStatistic.geographic_unit_id == GeographicUnit.id)
        .where(
            GeographicUnit.code == "IN",
            CrimeStatistic.reporting_year == (target_year if target_year in rape_years else latest_granular),
            CrimeStatistic.crime_domain == "rape_offender_relation",
            CrimeStatistic.metric_type == "share_pct",
        )
    )
    if known_share is not None:
        yr_lbl = target_year if target_year in rape_years else latest_granular
        insights.append(
            StatisticalObservation(
                id="known-offender-share",
                title=f"Offender Relationship Structure ({yr_lbl})",
                category="NCRB Table 3A.4 Disaggregation",
                summary=(
                    f"In {yr_lbl}, NCRB recorded offenders known to the survivor in {known_share:.1f}% of registered "
                    "Sec. 376 rape cases (family members, partners, neighbours, or acquaintances)."
                ),
                source_table=f"NCRB TABLE 3A.4 ({yr_lbl})",
            )
        )
    insights.append(
        StatisticalObservation(
            id="2023-coverage-transparency",
            title="2023 Release Boundary & State Disposal Scope",
            category="Coverage Transparency",
            summary=(
                "NCRB 2023 Snapshot (9-2023.pdf) confirms 448,211 Total Crimes Against Women (+0.7% vs 2022), "
                "but Chapter 3A Sec. 376 State spreadsheets are not yet released on ncrb.gov.in; 2022 remains the "
                "latest complete State/UT Rape dataset."
            ),
            source_table="NCRB 9-2023.pdf & TABLE 3A.5/3A.6",
        )
    )

    last_ingested = db.scalar(select(func.max(DatasetVersion.ingested_at)))
    return DashboardOverviewResponse(
        data_mode="VERIFIED_OFFICIAL",
        data_banner=OFFICIAL_DATA_BANNER,
        selected_year=target_year,
        available_years=all_years,
        granular_rape_years=rape_years,
        selected_metric=metric,
        metric_available=metric_available,
        metric_unavailable_reason=metric_reason,
        kpis=kpis,
        national_trend=trend_points,
        top_states=top_states,
        research_insights=insights,
        source_transparency=SourceTransparencyBadge(
            dataset_name="NCRB Crime in India (Chapter 3A Official Tables)",
            reporting_period=f"{all_years[0]}–{all_years[-1]}" if all_years else "2018–2023",
            latest_granular_year=latest_granular,
            latest_publication_year=latest_pub,
            last_ingested_at=last_ingested.isoformat() if last_ingested else None,
            source_status="Verified Official NCRB SQLite Store",
            data_notice=(
                f"Granular State/UT Sec. 376 Rape data covers {', '.join(map(str, rape_years))}; "
                "2018–2019 & 2023 cover official National/State CAW aggregates where published."
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
    ensure_official_data(db)
    all_years, rape_years = _get_year_sets(db)
    latest_granular = rape_years[-1] if rape_years else 2022
    target_year = year if year in all_years else latest_granular

    regions = ["ALL"] + sorted(
        list(
            db.scalars(
                select(GeographicUnit.region_zone)
                .where(GeographicUnit.unit_type.in_(["state", "union_territory"]))
                .distinct()
            ).all()
        )
    )
    states, metric_available, reason = _fetch_state_records(
        db, [target_year], metric=metric, region=region, search=search
    )
    if target_year not in rape_years and metric in {"count", "victims", "rate_per_100k"}:
        metric_available = False
        reason = (
            f"State/UT Sec. 376 Rape spreadsheets for {target_year} have not been published/ingested; "
            f"switch to {', '.join(map(str, rape_years))} for verified state-level Rape figures."
        )

    return GeographicAnalysisResponse(
        data_mode="VERIFIED_OFFICIAL",
        data_banner=OFFICIAL_DATA_BANNER,
        selected_year=target_year,
        available_years=all_years,
        granular_rape_years=rape_years,
        selected_metric=metric,
        metric_available=metric_available,
        metric_unavailable_reason=reason,
        regions=regions,
        states=states,
        denominator_methodology=(
            "State/UT rates per 100,000 female population use RGI/MoHFW Mid-Year Projected Female Population "
            "published in NCRB Table 3A.1. States/UTs may not be ranked as 'safe' or 'dangerous' purely from FIR volumes."
        ),
        map_architecture_status=(
            "Official NCRB State/UT records mapped to canonical 36 States/UTs (GeoJSON polygon vector layer ready for Phase 3 map binding)."
        ),
    )


def get_trends_patterns(
    db: Session,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> TrendsPatternsResponse:
    ensure_official_data(db)
    all_years, rape_years = _get_year_sets(db)
    s_year = start_year if start_year is not None else (all_years[0] if all_years else 2018)
    e_year = end_year if end_year is not None else (all_years[-1] if all_years else 2023)
    if s_year > e_year:
        s_year, e_year = e_year, s_year

    nat_rows = _get_national_series(db)
    filtered = [r for r in nat_rows if s_year <= r["year"] <= e_year]
    disagg_year = max([y for y in rape_years if y <= e_year], default=(rape_years[-1] if rape_years else 2022))

    in_geo = db.scalar(select(GeographicUnit).where(GeographicUnit.code == "IN"))
    offender_buckets: List[DemographicBucket] = []
    age_buckets: List[DemographicBucket] = []

    if in_geo is not None:
        # Table 3A.4 Offender Relationship breakdown
        rel_rows = db.execute(
            select(CrimeStatistic.sub_category, CrimeStatistic.metric_type, CrimeStatistic.normalized_value, CrimeStatistic.source_table)
            .where(
                CrimeStatistic.geographic_unit_id == in_geo.id,
                CrimeStatistic.reporting_year == disagg_year,
                CrimeStatistic.crime_domain == "rape_offender_relation",
                CrimeStatistic.normalized_value.is_not(None),
            )
        ).all()
        rel_map = {sub: (float(val), src) for sub, _, val, src in rel_rows}
        total_rel_cases = rel_map.get("Total Rape Cases (Known + Unknown)", (None, ""))[0]
        rel_order = [
            ("Friends / Online-Friends / Live-in Partners / Separated Husband", "Acquaintances, online contacts, live-in partners, or separated spouses"),
            ("Family Friends / Neighbours / Employer / Other Known Persons", "Family friends, neighbours, employers, or other known persons"),
            ("Family Members", "Immediate or extended family members"),
            ("Offenders Unknown or Not Identified", "Cases where offenders were unknown or not identified"),
        ]
        for cat, note in rel_order:
            if cat in rel_map:
                cnt, src = rel_map[cat]
                pct = round((cnt / total_rel_cases) * 100.0, 2) if total_rel_cases else None
                offender_buckets.append(
                    DemographicBucket(
                        category=cat,
                        count=int(round(cnt)),
                        share_pct=pct,
                        unit="cases",
                        year=disagg_year,
                        source_table=src,
                        note=note,
                    )
                )

        # Table 3A.3 Victim Age Group breakdown
        age_rows = db.execute(
            select(CrimeStatistic.sub_category, CrimeStatistic.normalized_value, CrimeStatistic.source_table)
            .where(
                CrimeStatistic.geographic_unit_id == in_geo.id,
                CrimeStatistic.reporting_year == disagg_year,
                CrimeStatistic.crime_domain == "rape_age_groups",
                CrimeStatistic.metric_type == "victims",
                CrimeStatistic.normalized_value.is_not(None),
            )
        ).all()
        age_map = {sub: (float(val), src) for sub, val, src in age_rows}
        total_victims = age_map.get("Total Rape Victims (All Ages)", (None, ""))[0]
        age_order = [
            ("Child Victims Subtotal (Below 18 Years)", "Girls / child victims under 18 years (IPC Sec. 376 reported under Table 3A.3)"),
            ("Adult: 18 to 30 Years", "Women victims aged 18 to below 30 years"),
            ("Adult: 30 to 45 Years", "Women victims aged 30 to below 45 years"),
            ("Adult: 45 to 60 Years", "Women victims aged 45 to below 60 years"),
            ("Adult: 60 Years & Above", "Women victims aged 60 years & above"),
        ]
        for cat, note in age_order:
            if cat in age_map:
                cnt, src = age_map[cat]
                pct = round((cnt / total_victims) * 100.0, 2) if total_victims else None
                age_buckets.append(
                    DemographicBucket(
                        category=cat,
                        count=int(round(cnt)),
                        share_pct=pct,
                        unit="female_victims",
                        year=disagg_year,
                        source_table=src,
                        note=note,
                    )
                )

    anomalies = [StatisticalObservation(**a) for a in detect_series_anomalies(filtered)]
    return TrendsPatternsResponse(
        data_mode="VERIFIED_OFFICIAL",
        data_banner=OFFICIAL_DATA_BANNER,
        start_year=s_year,
        end_year=e_year,
        available_years=all_years,
        disaggregation_year=disagg_year,
        series=[NationalTrendPoint(**r) for r in filtered],
        offender_relationship=offender_buckets,
        age_group_breakdown=age_buckets,
        anomalies=anomalies,
    )


def build_research_preview(db: Session, payload: ResearchPreviewRequest) -> ResearchPreviewResponse:
    ensure_official_data(db)
    all_years, rape_years = _get_year_sets(db)
    target_years = sorted({y for y in payload.years if y in all_years}) or list(rape_years or [2022])
    codes = [c.upper() for c in payload.state_codes] if payload.state_codes else None

    rows, metric_available, reason = _fetch_state_records(
        db, target_years, metric=payload.metric, state_codes=codes
    )
    rows.sort(key=lambda r: (r.year, r.state_name))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["# THE UNHEARD — Official NCRB Statistical Export (Verified DB Extract)"])
    writer.writerow(["# Note: Reported police FIRs under Principal Offence Rule; not societal prevalence."])
    writer.writerow(
        [
            "year",
            "state_code",
            "state_name",
            "unit_type",
            "region_zone",
            "sec376_rape_cases_registered",
            "sec376_female_victims",
            "sec376_rate_per_100k_female",
            "projected_female_pop_lakhs",
            "caw_total_cases_ipc_sll",
            "caw_chargesheet_pct_not_rape_only",
            "caw_conviction_pct_not_rape_only",
            "validation_status",
            "source_table",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.year,
                r.state_code,
                r.state_name,
                r.unit_type,
                r.region_zone,
                r.reported_cases if r.reported_cases is not None else "UNAVAILABLE",
                r.victims_count if r.victims_count is not None else "UNAVAILABLE",
                r.rate_per_100k_female if r.rate_per_100k_female is not None else "UNAVAILABLE",
                r.female_population_lakhs if r.female_population_lakhs is not None else "UNAVAILABLE",
                r.caw_total_cases if r.caw_total_cases is not None else "UNAVAILABLE",
                r.caw_charge_sheet_pct if r.caw_charge_sheet_pct is not None else "UNAVAILABLE",
                r.caw_conviction_pct if r.caw_conviction_pct is not None else "UNAVAILABLE",
                r.validation_status,
                r.source_table,
            ]
        )

    return ResearchPreviewResponse(
        data_mode="VERIFIED_OFFICIAL",
        data_banner=OFFICIAL_DATA_BANNER,
        metric=payload.metric,
        metric_available=metric_available,
        unavailable_reason=reason,
        years=target_years,
        state_codes=codes or [],
        rows=rows,
        csv_preview=buf.getvalue(),
    )


def get_datasets_report(db: Session) -> DatasetListResponse:
    ensure_official_data(db)
    rows = db.execute(
        select(Dataset, DatasetVersion, DataSource)
        .join(DatasetVersion, DatasetVersion.dataset_id == Dataset.id)
        .join(DataSource, Dataset.source_id == DataSource.id)
        .where(DatasetVersion.is_active.is_(True))
        .order_by(desc(DatasetVersion.reporting_year), Dataset.table_number)
    ).all()

    items = [
        DatasetVersionDetailSchema(
            dataset_key=ds.dataset_key,
            source_slug=src.slug,
            table_number=ds.table_number,
            title=ds.title,
            crime_domain=ds.crime_domain,
            granularity=ds.granularity,
            unit_description=ds.unit_description,
            reporting_year=ver.reporting_year,
            version_label=ver.version_label,
            file_format=ver.file_format,
            file_sha256=ver.file_sha256,
            record_count=ver.record_count,
            ingestion_status=ver.ingestion_status,
            ingested_at=ver.ingested_at,
            extraction_notes=ver.extraction_notes,
        )
        for ds, ver, src in rows
    ]
    total_crime = db.scalar(select(func.count(CrimeStatistic.id))) or 0
    total_pop = db.scalar(select(func.count(PopulationStatistic.id))) or 0
    latest_at = db.scalar(select(func.max(DatasetVersion.ingested_at)))
    return DatasetListResponse(
        total_datasets=len(items),
        total_crime_records=int(total_crime),
        total_population_records=int(total_pop),
        latest_ingested_at=latest_at,
        datasets=items,
    )


def get_data_quality_report(db: Session) -> DataQualityReportResponse:
    ensure_official_data(db)
    issue_rows = db.execute(
        select(DataQualityIssue, GeographicUnit)
        .outerjoin(GeographicUnit, DataQualityIssue.geographic_unit_id == GeographicUnit.id)
        .order_by(DataQualityIssue.severity, DataQualityIssue.id)
    ).all()

    sev_counts: Dict[str, int] = defaultdict(int)
    cat_counts: Dict[str, int] = defaultdict(int)
    items: List[DataQualityIssueSchema] = []
    for issue, geo in issue_rows:
        sev_counts[issue.severity] += 1
        cat_counts[issue.category] += 1
        items.append(
            DataQualityIssueSchema(
                id=issue.id,
                issue_code=issue.issue_code,
                severity=issue.severity,
                category=issue.category,
                reporting_year=issue.reporting_year,
                geo_code=geo.code if geo else None,
                geo_name=geo.canonical_name if geo else None,
                title=issue.title,
                description=issue.description,
                source_table=issue.source_table,
                resolved=issue.resolved,
                detected_at=issue.detected_at,
            )
        )

    val_rows = db.execute(
        select(CrimeStatistic.validation_status, func.count(CrimeStatistic.id)).group_by(CrimeStatistic.validation_status)
    ).all()
    val_breakdown = {str(st): int(cnt) for st, cnt in val_rows}

    return DataQualityReportResponse(
        total_issues=len(items),
        counts_by_severity=dict(sev_counts),
        counts_by_category=dict(cat_counts),
        validation_status_breakdown=val_breakdown,
        issues=items,
    )


def get_sources_methodology(db: Session) -> SourcesMethodologyResponse:
    ensure_official_data(db)
    src_rows = db.scalars(select(DataSource).order_by(desc(DataSource.reporting_period))).all()
    datasets = [
        DatasetSourceSchema(
            slug=s.slug,
            name=s.official_title,
            publisher=s.publisher,
            reporting_period=s.reporting_period,
            publication_date=s.publication_date,
            download_date=s.download_date,
            status=s.status,
            granularity=s.geographic_coverage,
            definitions_summary=(
                "Official NCRB Chapter 3A data under IPC Sec. 376 & Crime Against Women (IPC+SLL); "
                "Cases (I), Victims (V), Rate per Lakh Female Population (R) strictly separated."
            ),
            missing_data_notes=s.notes,
            source_url=s.source_url,
        )
        for s in src_rows
    ]
    ds_report = get_datasets_report(db)
    dq_report = get_data_quality_report(db)
    return SourcesMethodologyResponse(
        datasets=datasets,
        dataset_versions=ds_report.datasets,
        quality_summary=dq_report,
        methodology_sections=[MethodologySectionSchema(**m) for m in METHODOLOGY_SECTIONS],
    )


def get_dashboard_insights(
    db: Session,
    year: Optional[int] = None,
    state_code: str = "ALL",
    metric: MetricKey = "count",
    compare_code: Optional[str] = None,
) -> DashboardInsightsResponse:
    """Compute deterministic, source-traceable insights from validated DB records."""
    ensure_official_data(db)
    all_years, rape_years = _get_year_sets(db)
    latest_granular = rape_years[-1] if rape_years else 2022
    target_year = year if year in all_years else latest_granular
    norm_state = (state_code or "ALL").upper()
    norm_compare = compare_code.upper() if compare_code else None

    trend_rows = _get_national_series(db)
    current_pt = next((r for r in trend_rows if r["year"] == target_year), None)

    states, _, _ = _fetch_state_records(db, [target_year], metric=metric)
    selected_state = next((s for s in states if s.state_code == norm_state), None) if norm_state != "ALL" else None
    compare_state = next((s for s in states if s.state_code == norm_compare), None) if norm_compare else None

    # Resolve official NCRB source URL for the target year
    src_url = db.scalar(
        select(DataSource.source_url).where(DataSource.reporting_period.contains(str(target_year)))
    ) or "https://www.ncrb.gov.in/"

    insights: List[DeterministicInsight] = []

    # 1. Selected Year & Jurisdiction Baseline
    if selected_state is not None:
        if selected_state.reported_cases is not None and selected_state.rate_per_100k_female is not None:
            obs = (
                f"In {target_year}, {selected_state.state_name} recorded {selected_state.reported_cases:,} "
                f"Sec. 376 cases ({selected_state.victims_count:,} female victims) at "
                f"{selected_state.rate_per_100k_female:.1f} per 100,000 female population"
                + (f" (Rank #{selected_state.rank_by_selected})." if selected_state.rank_by_selected else ".")
            )
            interp = (
                "Police-recorded FIRs under the Principal Offence Rule reflect reporting volume and "
                "denominator size rather than underlying societal incidence."
            )
        elif selected_state.caw_total_cases is not None:
            obs = (
                f"In {target_year}, {selected_state.state_name} recorded {selected_state.caw_total_cases:,} "
                f"Total Crimes Against Women (IPC+SLL); Sec. 376 State spreadsheets are not published for {target_year}."
            )
            interp = (
                "Total CAW aggregates all crime heads against women and must not be equated with "
                "Sec. 376 Rape counts."
            )
        else:
            obs = f"No granular State/UT records are available for {selected_state.state_name} in {target_year}."
            interp = "NCRB has not published State-level Chapter 3A spreadsheets for this reporting year."

        insights.append(
            DeterministicInsight(
                id=f"baseline-{norm_state}-{target_year}",
                category="Selected Jurisdiction",
                title=f"{selected_state.state_name} Baseline ({target_year})",
                observed_data=obs,
                interpretation=interp,
                reporting_year=target_year,
                metric=metric,
                source_table=selected_state.source_table,
                source_url=src_url,
            )
        )
    elif current_pt is not None:
        if current_pt.get("reported_cases") is not None:
            obs = (
                f"All-India {target_year} Sec. 376 totals: {current_pt['reported_cases']:,} cases, "
                f"{current_pt['victims_count']:,} female victims, and {current_pt['rate_per_100k_female']:.1f} "
                f"per 100,000 female population."
            )
            interp = (
                "Victims exceed case counts when a single FIR involves multiple survivors; "
                "rates use RGI/MoHFW mid-year female projections."
            )
        else:
            caw_val = current_pt.get("caw_total_cases")
            obs = (
                f"All-India {target_year} Total CAW (IPC+SLL) stood at {caw_val:,} cases; "
                f"Sec. 376 State/National Excel tables are unavailable for {target_year}."
                if caw_val is not None
                else f"No Sec. 376 or CAW totals available for {target_year}."
            )
            interp = (
                "NCRB 2018–2019 and 2023 records in this store cover Total CAW aggregates; "
                "granular Sec. 376 disaggregations span 2020–2022."
            )

        insights.append(
            DeterministicInsight(
                id=f"baseline-IN-{target_year}",
                category="National Baseline",
                title=f"All-India Reporting Baseline ({target_year})",
                observed_data=obs,
                interpretation=interp,
                reporting_year=target_year,
                metric=metric,
                source_table=current_pt["source_table"],
                source_url=src_url,
            )
        )

    # 2. Largest Year-on-Year Shift (National Series)
    caw_yoy_rows = [r for r in trend_rows if r.get("caw_yoy_change_pct") is not None]
    if caw_yoy_rows:
        max_inc = max(caw_yoy_rows, key=lambda r: r["caw_yoy_change_pct"])
        max_dec = min(caw_yoy_rows, key=lambda r: r["caw_yoy_change_pct"])
        insights.append(
            DeterministicInsight(
                id="yoy-extremes",
                category="Longitudinal Shift",
                title="Largest National Year-on-Year Shifts (2018–2023)",
                observed_data=(
                    f"Largest CAW increase: {max_inc['year']} ({max_inc['caw_yoy_change_pct']:+.1f}% YoY to "
                    f"{max_inc['caw_total_cases']:,}); largest decline: {max_dec['year']} "
                    f"({max_dec['caw_yoy_change_pct']:+.1f}% YoY to {max_dec['caw_total_cases']:,})."
                ),
                interpretation=(
                    "The 2020 contraction and 2021 rebound coincide with COVID-19 mobility restrictions "
                    "and subsequent resumption of police-station reporting."
                ),
                reporting_year=target_year,
                metric=metric,
                source_table="NCRB TABLE 3A.1 (2018–2023)",
                source_url=src_url,
            )
        )

    # 3. State-vs-State Difference OR Top State Leader
    if selected_state is not None and compare_state is not None and selected_state.state_code != compare_state.state_code:
        if (
            selected_state.reported_cases is not None
            and compare_state.reported_cases is not None
            and selected_state.rate_per_100k_female is not None
            and compare_state.rate_per_100k_female is not None
        ):
            case_diff = selected_state.reported_cases - compare_state.reported_cases
            rate_diff = selected_state.rate_per_100k_female - compare_state.rate_per_100k_female
            insights.append(
                DeterministicInsight(
                    id=f"compare-{selected_state.state_code}-{compare_state.state_code}-{target_year}",
                    category="State Comparison",
                    title=f"{selected_state.state_name} vs. {compare_state.state_name} ({target_year})",
                    observed_data=(
                        f"{selected_state.state_name} reported {case_diff:+,} Sec. 376 cases compared to "
                        f"{compare_state.state_name} ({selected_state.reported_cases:,} vs. {compare_state.reported_cases:,}), "
                        f"and a {rate_diff:+.1f} per 100k female rate difference "
                        f"({selected_state.rate_per_100k_female:.1f} vs. {compare_state.rate_per_100k_female:.1f})."
                    ),
                    interpretation=(
                        "Comparing per-100k female population rates alongside raw counts adjusts for "
                        "state population scale, though reporting propensity still varies."
                    ),
                    reporting_year=target_year,
                    metric=metric,
                    source_table=selected_state.source_table,
                    source_url=src_url,
                )
            )
    else:
        ranked = [s for s in states if s.rank_by_selected == 1]
        if ranked:
            leader = ranked[0]
            val_str = (
                f"{leader.rate_per_100k_female:.1f} per 100k female pop."
                if metric == "rate_per_100k" and leader.rate_per_100k_female is not None
                else f"{leader.victims_count:,} female victims"
                if metric == "victims" and leader.victims_count is not None
                else f"{leader.reported_cases:,} Sec. 376 cases"
                if leader.reported_cases is not None
                else "Unavailable"
            )
            insights.append(
                DeterministicInsight(
                    id=f"leader-{target_year}-{metric}",
                    category="Jurisdiction Ranking",
                    title=f"Highest Ranked Jurisdiction ({target_year})",
                    observed_data=f"{leader.state_name} ({leader.region_zone}) ranks #1 for the active metric at {val_str}.",
                    interpretation=(
                        "High registered counts or rates can reflect higher FIR registration accessibility "
                        "as well as underlying incidence; rankings should not be read as safety indices."
                    ),
                    reporting_year=target_year,
                    metric=metric,
                    source_table=leader.source_table,
                    source_url=src_url,
                )
            )

    # 4. Data Availability or Disposal Boundary Insight
    if current_pt and current_pt.get("charge_sheet_pct") is not None and current_pt.get("conviction_pct") is not None:
        gap = round(current_pt["charge_sheet_pct"] - current_pt["conviction_pct"], 1)
        insights.append(
            DeterministicInsight(
                id=f"disposal-gap-{target_year}",
                category="Disposal Boundary",
                title=f"Police Chargesheet vs. Court Conviction ({target_year})",
                observed_data=(
                    f"All-India Sec. 376 chargesheeting was {current_pt['charge_sheet_pct']:.1f}% while "
                    f"court conviction was {current_pt['conviction_pct']:.1f}% ({gap:.1f} pp gap; "
                    f"{current_pt['trial_pendency_pct']:.1f}% trial pendency)."
                ),
                interpretation=(
                    "NCRB publishes Sec. 376 disposal rates only at the All-India level; State Tables 3A.6 & 3A.8 "
                    "aggregate all Crimes Against Women and are not substituted here."
                ),
                reporting_year=target_year,
                metric=metric,
                source_table="NCRB TABLES 3A.5 & 3A.7",
                source_url=src_url,
            )
        )
    else:
        insights.append(
            DeterministicInsight(
                id=f"coverage-gap-{target_year}",
                category="Data Coverage Gap",
                title=f"Granular Sec. 376 Coverage Gap ({target_year})",
                observed_data=(
                    f"State-level Sec. 376 Rape spreadsheets and National Sec. 376 disposal tables "
                    f"are unavailable in the ingested NCRB store for {target_year}."
                ),
                interpretation=(
                    "Missing years are preserved as Unavailable rather than interpolated; switch to "
                    "2020–2022 for complete State/UT Sec. 376 breakdowns."
                ),
                reporting_year=target_year,
                metric=metric,
                source_table="NCRB Coverage Audit",
                source_url=src_url,
            )
        )

    return DashboardInsightsResponse(
        selected_year=target_year,
        selected_state_code=selected_state.state_code if selected_state else "ALL",
        selected_state_name=selected_state.state_name if selected_state else "All India (National)",
        selected_metric=metric,
        calculation_mode="deterministic_db",
        llm_provider_configured=False,
        insights=insights,
    )

