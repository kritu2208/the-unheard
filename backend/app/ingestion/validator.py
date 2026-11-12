from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.normalizer import detect_boundary_footnote_notes, resolve_canonical_geo
from app.ingestion.parsers import ParsedCrimeObservation, ParsedPopulationObservation
from app.models.records import CrimeStatistic, DataQualityIssue, GeographicUnit

CURRENT_MAX_VALID_YEAR = 2026


@dataclass
class ValidatedCrimeRecord:
    obs: ParsedCrimeObservation
    geo_code: str
    validation_status: str  # verified | warning | needs_review | rejected
    validation_notes: str


@dataclass
class ValidationIssueDraft:
    issue_code: str
    severity: str  # info | warning | error | critical
    category: str
    title: str
    description: str
    source_table: str
    reporting_year: Optional[int] = None
    geo_code: Optional[str] = None
    affected_record_ref: str = ""


def validate_parsed_crime_rows(
    rows: List[ParsedCrimeObservation],
    source_table_fallback: str,
) -> Tuple[List[ValidatedCrimeRecord], List[ValidationIssueDraft]]:
    """Validate normalized crime observations without silently discarding questionable records."""
    validated: List[ValidatedCrimeRecord] = []
    issues: List[ValidationIssueDraft] = []
    seen_keys: set[Tuple[int, str, str, str, str, str]] = set()

    # Track sums of states/UTs vs All-India total for internal cross-check
    component_sums: Dict[Tuple[int, str, str, str, str], float] = defaultdict(float)
    reported_all_india: Dict[Tuple[int, str, str, str, str], float] = {}

    for obs in rows:
        geo = resolve_canonical_geo(obs.raw_geo_name)
        if geo is None:
            issues.append(
                ValidationIssueDraft(
                    issue_code="GEO_UNMAPPED",
                    severity="error",
                    category="geo_normalization",
                    title=f"Unmapped geographic identifier: {obs.raw_geo_name}",
                    description=f"Could not map '{obs.raw_geo_name}' in {obs.source_table} to a canonical Indian State/UT.",
                    source_table=obs.source_table or source_table_fallback,
                    reporting_year=obs.reporting_year,
                    affected_record_ref=obs.source_page_or_row,
                )
            )
            continue

        status = "verified"
        notes: List[str] = detect_boundary_footnote_notes(obs.raw_geo_name, obs.reporting_year)

        # Year check
        if obs.reporting_year < 1953 or obs.reporting_year > CURRENT_MAX_VALID_YEAR:
            status = "rejected"
            notes.append(f"Invalid reporting year {obs.reporting_year}.")
            issues.append(
                ValidationIssueDraft(
                    issue_code="INVALID_YEAR",
                    severity="error",
                    category="invalid_year",
                    title=f"Invalid reporting year {obs.reporting_year}",
                    description=f"Year {obs.reporting_year} outside NCRB publishing bounds in {obs.source_table}.",
                    source_table=obs.source_table,
                    reporting_year=obs.reporting_year,
                    geo_code=geo.code,
                    affected_record_ref=obs.source_page_or_row,
                )
            )

        # Missing value check
        if obs.normalized_value is None:
            if status != "rejected":
                status = "warning"
            notes.append(f"Missing/non-numeric source value ({obs.raw_value!r}) preserved without zero-substitution.")
            issues.append(
                ValidationIssueDraft(
                    issue_code="MISSING_NUMERIC_VALUE",
                    severity="warning",
                    category="missing_data",
                    title=f"Missing numeric value for {geo.canonical_name} ({obs.reporting_year})",
                    description=f"{obs.crime_head} / {obs.sub_category} ({obs.metric_type}) has raw value {obs.raw_value!r}.",
                    source_table=obs.source_table,
                    reporting_year=obs.reporting_year,
                    geo_code=geo.code,
                    affected_record_ref=obs.source_page_or_row,
                )
            )

        # Negative value check
        elif obs.normalized_value < 0:
            status = "error" if status != "rejected" else status
            notes.append(f"Negative count/value encountered: {obs.normalized_value}.")
            issues.append(
                ValidationIssueDraft(
                    issue_code="NEGATIVE_VALUE",
                    severity="error",
                    category="negative_value",
                    title=f"Negative statistic detected in {geo.canonical_name} ({obs.reporting_year})",
                    description=f"{obs.crime_head} / {obs.metric_type} = {obs.normalized_value}. Preserved with error status.",
                    source_table=obs.source_table,
                    reporting_year=obs.reporting_year,
                    geo_code=geo.code,
                    affected_record_ref=obs.source_page_or_row,
                )
            )

        # Invalid percentage check
        if obs.unit == "percent" and obs.normalized_value is not None:
            if obs.normalized_value < 0 or obs.normalized_value > 100:
                if status == "verified":
                    status = "warning"
                notes.append(f"Percentage outside [0, 100]: {obs.normalized_value}%.")
                issues.append(
                    ValidationIssueDraft(
                        issue_code="INVALID_PERCENTAGE",
                        severity="warning",
                        category="invalid_percentage",
                        title=f"Out-of-bounds percentage ({obs.normalized_value}%) in {geo.canonical_name}",
                        description=f"{obs.crime_head} {obs.metric_type} reported {obs.normalized_value}% in {obs.source_table}.",
                        source_table=obs.source_table,
                        reporting_year=obs.reporting_year,
                        geo_code=geo.code,
                        affected_record_ref=obs.source_page_or_row,
                    )
                )

        # Source reference check
        if not obs.source_table or not obs.source_table.strip():
            status = "warning" if status == "verified" else status
            notes.append("Missing source table citation.")
            issues.append(
                ValidationIssueDraft(
                    issue_code="MISSING_SOURCE_REF",
                    severity="error",
                    category="missing_source_ref",
                    title=f"Missing source table reference for {geo.canonical_name}",
                    description="Observation lacks an explicit source_table reference.",
                    source_table=source_table_fallback,
                    reporting_year=obs.reporting_year,
                    geo_code=geo.code,
                )
            )

        # Intra-batch duplicate check
        dup_key = (
            obs.reporting_year,
            geo.code,
            obs.crime_domain,
            obs.crime_head,
            obs.sub_category,
            obs.metric_type,
        )
        if dup_key in seen_keys:
            issues.append(
                ValidationIssueDraft(
                    issue_code="DUPLICATE_IN_BATCH",
                    severity="warning",
                    category="duplicate",
                    title=f"Duplicate observation skipped for {geo.canonical_name} ({obs.reporting_year})",
                    description=f"Duplicate entry for {obs.crime_domain} / {obs.sub_category} / {obs.metric_type} in {obs.source_table}.",
                    source_table=obs.source_table,
                    reporting_year=obs.reporting_year,
                    geo_code=geo.code,
                    affected_record_ref=obs.source_page_or_row,
                )
            )
            continue
        seen_keys.add(dup_key)

        if obs.unit in {"cases", "female_victims"} and obs.normalized_value is not None:
            agg_key = (obs.reporting_year, obs.crime_domain, obs.crime_head, obs.sub_category, obs.metric_type)
            if geo.unit_type in {"state", "union_territory"}:
                component_sums[agg_key] += obs.normalized_value
            elif geo.code == "IN":
                reported_all_india[agg_key] = obs.normalized_value

        validated.append(
            ValidatedCrimeRecord(
                obs=obs,
                geo_code=geo.code,
                validation_status=status,
                validation_notes=" ".join(notes),
            )
        )

    # Cross-check sum of States + UTs against TOTAL ALL INDIA
    for agg_key, india_total in reported_all_india.items():
        if agg_key not in component_sums:
            continue
        calc_sum = component_sums[agg_key]
        if abs(calc_sum - india_total) > 0.5:
            yr, domain, head, sub_cat, mtype = agg_key
            issues.append(
                ValidationIssueDraft(
                    issue_code="INCONSISTENT_NATIONAL_TOTAL",
                    severity="error",
                    category="inconsistent_total",
                    title=f"State+UT sum mismatch for {head} ({yr})",
                    description=(
                        f"Sum of individual States/UTs ({calc_sum:.0f}) differs from reported TOTAL ALL INDIA "
                        f"({india_total:.0f}) for {domain} / {sub_cat} / {mtype}."
                    ),
                    source_table=source_table_fallback,
                    reporting_year=yr,
                    geo_code="IN",
                )
            )

    return validated, issues


def validate_population_rows(
    rows: List[ParsedPopulationObservation],
) -> Tuple[List[Tuple[ParsedPopulationObservation, str]], List[ValidationIssueDraft]]:
    """Validate official population denominators and detect unmapped/negative entries."""
    valid_rows: List[Tuple[ParsedPopulationObservation, str]] = []
    issues: List[ValidationIssueDraft] = []
    for pop in rows:
        geo = resolve_canonical_geo(pop.raw_geo_name)
        if geo is None:
            issues.append(
                ValidationIssueDraft(
                    issue_code="POP_GEO_UNMAPPED",
                    severity="warning",
                    category="geo_normalization",
                    title=f"Unmapped population row: {pop.raw_geo_name}",
                    description=f"Skipped unmapped geographic label in {pop.source_table}.",
                    source_table=pop.source_table,
                    reporting_year=pop.reporting_year,
                )
            )
            continue
        if pop.population_lakhs is None or pop.population_lakhs <= 0:
            issues.append(
                ValidationIssueDraft(
                    issue_code="INVALID_POPULATION",
                    severity="error",
                    category="negative_value",
                    title=f"Non-positive population value for {geo.canonical_name} ({pop.reporting_year})",
                    description=f"Population value {pop.population_lakhs!r} in {pop.source_table} cannot be used as rate denominator.",
                    source_table=pop.source_table,
                    reporting_year=pop.reporting_year,
                    geo_code=geo.code,
                )
            )
            continue
        valid_rows.append((pop, geo.code))
    return valid_rows, issues


def run_cross_year_audit(db: Session, geo_lookup: Dict[str, GeographicUnit]) -> List[ValidationIssueDraft]:
    """Check cross-year YoY jumps (>=30%) on verified Rape and CAW counts across the DB."""
    issues: List[ValidationIssueDraft] = []
    rows = db.execute(
        select(
            CrimeStatistic.reporting_year,
            CrimeStatistic.geographic_unit_id,
            CrimeStatistic.crime_domain,
            CrimeStatistic.crime_head,
            CrimeStatistic.normalized_value,
            CrimeStatistic.source_table,
        )
        .where(
            CrimeStatistic.crime_domain.in_(["rape_ipc_376", "caw_total"]),
            CrimeStatistic.sub_category == "Total",
            CrimeStatistic.metric_type == "cases_registered",
            CrimeStatistic.normalized_value.is_not(None),
        )
        .order_by(CrimeStatistic.geographic_unit_id, CrimeStatistic.crime_domain, CrimeStatistic.reporting_year)
    ).all()

    by_id_to_geo = {g.id: g for g in geo_lookup.values()}
    # Deduplicate same geo+domain+year preferring latest edition source_table lexicographically
    latest_val: Dict[Tuple[int, str, int], Tuple[float, str, str]] = {}
    for yr, gid, domain, head, val, src_tbl in rows:
        key = (gid, domain, yr)
        prev = latest_val.get(key)
        if prev is None or src_tbl > prev[2]:
            latest_val[key] = (float(val), head, src_tbl)

    series_map: Dict[Tuple[int, str], List[Tuple[int, float, str, str]]] = defaultdict(list)
    for (gid, domain, yr), (val, head, src_tbl) in latest_val.items():
        series_map[(gid, domain)].append((yr, val, head, src_tbl))

    for (gid, domain), pts in series_map.items():
        pts.sort(key=lambda x: x[0])
        geo = by_id_to_geo.get(gid)
        if not geo or geo.unit_type == "subtotal":
            continue
        for i in range(1, len(pts)):
            y0, v0, _, _ = pts[i - 1]
            y1, v1, head, src_tbl = pts[i]
            if y1 - y0 != 1 or v0 < 50:
                continue
            pct = ((v1 - v0) / v0) * 100.0
            if abs(pct) >= 30.0:
                direction = "increase" if pct > 0 else "decrease"
                issues.append(
                    ValidationIssueDraft(
                        issue_code="LARGE_YOY_SHIFT",
                        severity="warning" if abs(pct) >= 45.0 else "info",
                        category="yoy_outlier",
                        title=f"{geo.canonical_name}: {abs(pct):.1f}% YoY {direction} in {head} ({y0}->{y1})",
                        description=(
                            f"Reported FIR count changed from {int(v0):,} ({y0}) to {int(v1):,} ({y1}) "
                            f"({pct:+.1f}%). Large shifts may reflect reporting access, registration drives, or administrative boundary changes rather than prevalence shifts."
                        ),
                        source_table=src_tbl,
                        reporting_year=y1,
                        geo_code=geo.code,
                    )
                )

    return issues

