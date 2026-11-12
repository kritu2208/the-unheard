import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ingestion.normalizer import (
    build_record_fingerprint,
    compute_file_sha256,
    ensure_geographic_units,
)
from app.ingestion.parsers import (
    ParseResult,
    parse_csv_dataset,
    parse_ncrb_pdf,
    parse_table_3a1,
    parse_table_3a2,
    parse_table_3a3,
    parse_table_3a4,
    parse_table_3a5_or_3a7,
    parse_table_3a6_or_3a8,
    parse_table_3a11,
)
from app.ingestion.validator import (
    ValidationIssueDraft,
    run_cross_year_audit,
    validate_parsed_crime_rows,
    validate_population_rows,
)
from app.models.records import (
    CrimeStatistic,
    DataQualityIssue,
    DataSource,
    Dataset,
    DatasetVersion,
    GeographicUnit,
    PopulationStatistic,
)


def resolve_project_root() -> Path:
    """Locate THE-UNHEARD repository root containing data/ and backend/."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "documentation" / "source_registry.json").exists():
            return parent
    return here.parents[3]


@dataclass
class IngestionSummary:
    versions_processed: int = 0
    versions_skipped_duplicate: int = 0
    crime_records_written: int = 0
    population_records_written: int = 0
    quality_issues_logged: int = 0


def _infer_domain_and_granularity(table_number: str, ingestion_role: str) -> tuple[str, str]:
    mapping = {
        "caw_multiyear_and_female_population": ("caw_total", "state_ut"),
        "state_crime_heads_ivr": ("rape_ipc_376", "state_ut"),
        "rape_victim_age_groups": ("rape_age_groups", "state_ut"),
        "rape_offender_relation": ("rape_offender_relation", "state_ut"),
        "national_police_disposal": ("rape_national_police_disposal", "national"),
        "state_caw_police_disposal": ("caw_state_police_disposal", "state_ut"),
        "national_court_disposal": ("rape_national_court_disposal", "national"),
        "state_caw_court_disposal": ("caw_state_court_disposal", "state_ut"),
        "rape_section_wise": ("rape_section_wise", "state_ut"),
        "pdf_rape_victim_age_groups": ("rape_age_groups", "national"),
        "pdf_rape_offender_relation": ("rape_offender_relation", "national"),
        "pdf_national_caw_2023": ("caw_total", "national"),
        "pdf_total_population": ("population_projection", "state_ut"),
        "pdf_inspection_only": ("documentation", "national"),
        "archival_reference": ("archival_pdf", "state_ut"),
    }
    return mapping.get(ingestion_role, (table_number.lower().replace(" ", "_"), "state_ut"))


def _dispatch_parse(file_path: Path, table_number: str, edition_year: int, ingestion_role: str) -> Optional[ParseResult]:
    suffix = file_path.suffix.lower()
    if ingestion_role == "archival_reference":
        return None
    if suffix in {".xlsx", ".xls"}:
        upper_tbl = table_number.upper().strip()
        if "3A.11" in upper_tbl:
            return parse_table_3a11(file_path, edition_year)
        if "3A.1" in upper_tbl:
            return parse_table_3a1(file_path, edition_year)
        if "3A.2" in upper_tbl:
            return parse_table_3a2(file_path, edition_year)
        if "3A.3" in upper_tbl:
            return parse_table_3a3(file_path, edition_year)
        if "3A.4" in upper_tbl:
            return parse_table_3a4(file_path, edition_year)
        if "3A.5" in upper_tbl:
            return parse_table_3a5_or_3a7(file_path, edition_year, "TABLE 3A.5")
        if "3A.7" in upper_tbl:
            return parse_table_3a5_or_3a7(file_path, edition_year, "TABLE 3A.7")
        if "3A.6" in upper_tbl:
            return parse_table_3a6_or_3a8(file_path, edition_year, "TABLE 3A.6")
        if "3A.8" in upper_tbl:
            return parse_table_3a6_or_3a8(file_path, edition_year, "TABLE 3A.8")
    elif suffix == ".csv":
        return parse_csv_dataset(file_path, edition_year, table_code=table_number)
    elif suffix == ".pdf":
        return parse_ncrb_pdf(file_path, edition_year, ingestion_role)
    return None


def _persist_issues(
    db: Session,
    drafts: List[ValidationIssueDraft],
    geo_lookup: Dict[str, GeographicUnit],
    dataset_version_id: Optional[int],
) -> int:
    count = 0
    for d in drafts:
        geo = geo_lookup.get(d.geo_code) if d.geo_code else None
        db.add(
            DataQualityIssue(
                dataset_version_id=dataset_version_id,
                geographic_unit_id=geo.id if geo else None,
                reporting_year=d.reporting_year,
                issue_code=d.issue_code,
                severity=d.severity,
                category=d.category,
                title=d.title,
                description=d.description,
                source_table=d.source_table,
                affected_record_ref=d.affected_record_ref,
                resolved=False,
            )
        )
        count += 1
    return count


def _ingest_single_file(
    db: Session,
    dataset: Dataset,
    file_path: Path,
    table_number: str,
    edition_year: int,
    ingestion_role: str,
    geo_lookup: Dict[str, GeographicUnit],
    summary: IngestionSummary,
    force: bool = False,
) -> None:
    if not file_path.exists():
        _persist_issues(
            db,
            [
                ValidationIssueDraft(
                    issue_code="MISSING_RAW_FILE",
                    severity="error",
                    category="missing_data",
                    title=f"Registered raw file missing: {file_path.name}",
                    description=f"Expected file at {file_path} was not found on disk.",
                    source_table=table_number,
                    reporting_year=edition_year,
                )
            ],
            geo_lookup,
            dataset_version_id=None,
        )
        summary.quality_issues_logged += 1
        return

    file_hash = compute_file_sha256(str(file_path))
    existing_ver = db.scalar(
        select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset.id,
            DatasetVersion.file_sha256 == file_hash,
            DatasetVersion.reporting_year == edition_year,
        )
    )
    if existing_ver is not None and not force:
        summary.versions_skipped_duplicate += 1
        return

    if existing_ver is not None and force:
        db.delete(existing_ver)
        db.flush()

    parse_res = _dispatch_parse(file_path, table_number, edition_year, ingestion_role)
    if parse_res is None:
        # Register archival PDF reference version cleanly with 0 extracted rows
        ver = DatasetVersion(
            dataset_id=dataset.id,
            version_label=f"v{edition_year}.{file_hash[:8]}",
            file_path=str(file_path),
            file_format=file_path.suffix.lstrip(".").lower(),
            file_sha256=file_hash,
            reporting_year=edition_year,
            record_count=0,
            ingestion_status="archived_reference",
            extraction_notes="Preserved original official PDF archival copy; tabular ingestion uses the companion official .xlsx.",
            is_active=True,
        )
        db.add(ver)
        db.flush()
        summary.versions_processed += 1
        return

    validated_crime, crime_issues = validate_parsed_crime_rows(parse_res.crime_rows, table_number)
    validated_pop, pop_issues = validate_population_rows(parse_res.population_rows)

    for warn in parse_res.warnings:
        crime_issues.append(
            ValidationIssueDraft(
                issue_code="PARSER_PARTIAL_OR_NOTE",
                severity="info" if parse_res.status == "completed" else "warning",
                category="pdf_limitation" if file_path.suffix.lower() == ".pdf" else "missing_data",
                title=f"{table_number} ({edition_year}) extraction note",
                description=warn,
                source_table=table_number,
                reporting_year=edition_year,
            )
        )

    notes_combined = " | ".join(parse_res.extraction_notes + parse_res.warnings)
    version = DatasetVersion(
        dataset_id=dataset.id,
        version_label=f"v{edition_year}.{file_hash[:8]}",
        file_path=str(file_path),
        file_format=file_path.suffix.lstrip(".").lower(),
        file_sha256=file_hash,
        reporting_year=edition_year,
        record_count=0,
        ingestion_status=parse_res.status,
        extraction_notes=notes_combined,
        is_active=True,
    )
    db.add(version)
    db.flush()

    written = 0
    for rec in validated_crime:
        geo = geo_lookup[rec.geo_code]
        fp = build_record_fingerprint(
            dataset_key=dataset.dataset_key,
            reporting_year=rec.obs.reporting_year,
            geo_code=geo.code,
            crime_domain=rec.obs.crime_domain,
            crime_head=rec.obs.crime_head,
            sub_category=rec.obs.sub_category,
            metric_type=rec.obs.metric_type,
        )
        existing_obs = db.scalar(select(CrimeStatistic).where(CrimeStatistic.record_fingerprint == fp))
        if existing_obs is not None:
            continue
        db.add(
            CrimeStatistic(
                dataset_version_id=version.id,
                geographic_unit_id=geo.id,
                reporting_year=rec.obs.reporting_year,
                crime_domain=rec.obs.crime_domain,
                crime_head=rec.obs.crime_head,
                sub_category=rec.obs.sub_category,
                metric_type=rec.obs.metric_type,
                unit=rec.obs.unit,
                raw_geo_name=rec.obs.raw_geo_name,
                raw_value=rec.obs.raw_value,
                normalized_value=rec.obs.normalized_value,
                denominator_scope=rec.obs.denominator_scope,
                source_table=rec.obs.source_table,
                source_page_or_row=rec.obs.source_page_or_row,
                is_estimated=rec.obs.is_estimated,
                validation_status=rec.validation_status,
                validation_notes=rec.validation_notes,
                record_fingerprint=fp,
            )
        )
        written += 1

    pop_written = 0
    for pop_obs, geo_code in validated_pop:
        geo = geo_lookup[geo_code]
        fp = build_record_fingerprint(
            dataset_key=dataset.dataset_key,
            reporting_year=pop_obs.reporting_year,
            geo_code=geo.code,
            crime_domain="population_projection",
            crime_head=f"Population ({pop_obs.denominator_scope})",
            sub_category=pop_obs.denominator_scope,
            metric_type="population_lakhs",
        )
        existing_pop = db.scalar(select(PopulationStatistic).where(PopulationStatistic.record_fingerprint == fp))
        if existing_pop is not None:
            continue
        db.add(
            PopulationStatistic(
                dataset_version_id=version.id,
                geographic_unit_id=geo.id,
                reporting_year=pop_obs.reporting_year,
                denominator_scope=pop_obs.denominator_scope,
                population_lakhs=pop_obs.population_lakhs or 0.0,
                raw_geo_name=pop_obs.raw_geo_name,
                raw_value=pop_obs.raw_value,
                source_table=pop_obs.source_table,
                source_notes=pop_obs.source_notes,
                validation_status="verified",
                record_fingerprint=fp,
            )
        )
        pop_written += 1

    version.record_count = written + pop_written
    summary.versions_processed += 1
    summary.crime_records_written += written
    summary.population_records_written += pop_written
    summary.quality_issues_logged += _persist_issues(
        db, crime_issues + pop_issues, geo_lookup, dataset_version_id=version.id
    )


def _refresh_global_audits_and_exports(db: Session, project_root: Path, geo_lookup: Dict[str, GeographicUnit]) -> int:
    """Run cross-year YoY + breakpoint checks and export normalized processed CSV artifacts."""
    db.execute(
        delete(DataQualityIssue).where(
            DataQualityIssue.issue_code.in_(["LARGE_YOY_SHIFT", "LEGAL_CLASSIFICATION_SHIFT", "NCRB_2023_TABLE_GAP"])
        )
    )
    db.flush()

    global_issues = run_cross_year_audit(db, geo_lookup)
    global_issues.extend(
        [
            ValidationIssueDraft(
                issue_code="LEGAL_CLASSIFICATION_SHIFT",
                severity="info",
                category="legal_breakpoint",
                title="2013 & 2024 Statutory Classification Breakpoints",
                description=(
                    "The Criminal Law (Amendment) Act, 2013 expanded Section 375/376 IPC definitions; pre-2013 and post-2013 counts "
                    "are not strictly comparable. From 1 July 2024, the Bharatiya Nyaya Sanhita (BNS 2023, Sec. 63-71) replaced IPC Sec. 376."
                ),
                source_table="IPC Sec. 376 / BNS Sec. 63-71",
                reporting_year=2024,
            ),
            ValidationIssueDraft(
                issue_code="NCRB_2023_TABLE_GAP",
                severity="warning",
                category="missing_data",
                title="NCRB 2023 Granular State/UT Rape Tables (Chapter 3A) Unavailable on Portal",
                description=(
                    "NCRB has published the 2023 Crime in India overview snapshots (9-2023.pdf: Total Crime Against Women = 448,211; rate 66.2), "
                    "but individual Chapter 3A Excel tables (State/UT Sec. 376 Rape, age groups, offender relation, disposal) are absent from "
                    "crime-in-india-table-content.html?year=2023 as of 2026-11-11. Granular 2023 metrics are explicitly marked Unavailable."
                ),
                source_table="crime-in-india-year-wise.html?year=2023",
                reporting_year=2023,
            ),
        ]
    )
    logged = _persist_issues(db, global_issues, geo_lookup, dataset_version_id=None)

    processed_dir = project_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Export Rape Sec. 376 IPC state+national flat CSV
    rape_rows = db.execute(
        select(
            CrimeStatistic.reporting_year,
            GeographicUnit.code,
            GeographicUnit.canonical_name,
            GeographicUnit.unit_type,
            CrimeStatistic.metric_type,
            CrimeStatistic.unit,
            CrimeStatistic.normalized_value,
            CrimeStatistic.raw_value,
            CrimeStatistic.source_table,
            CrimeStatistic.validation_status,
        )
        .join(GeographicUnit, CrimeStatistic.geographic_unit_id == GeographicUnit.id)
        .where(CrimeStatistic.crime_domain == "rape_ipc_376", CrimeStatistic.sub_category == "Total")
        .order_by(CrimeStatistic.reporting_year, GeographicUnit.canonical_name, CrimeStatistic.metric_type)
    ).all()
    if rape_rows:
        pd.DataFrame(
            rape_rows,
            columns=[
                "reporting_year",
                "geo_code",
                "state_ut_name",
                "unit_type",
                "metric_type",
                "unit",
                "normalized_value",
                "raw_value",
                "source_table",
                "validation_status",
            ],
        ).to_csv(processed_dir / "rape_state_statistics_official.csv", index=False)

    # Export CAW totals flat CSV
    caw_rows = db.execute(
        select(
            CrimeStatistic.reporting_year,
            GeographicUnit.code,
            GeographicUnit.canonical_name,
            CrimeStatistic.metric_type,
            CrimeStatistic.normalized_value,
            CrimeStatistic.source_table,
        )
        .join(GeographicUnit, CrimeStatistic.geographic_unit_id == GeographicUnit.id)
        .where(CrimeStatistic.crime_domain == "caw_total", CrimeStatistic.sub_category == "Total")
        .order_by(CrimeStatistic.reporting_year, GeographicUnit.canonical_name, CrimeStatistic.source_table)
    ).all()
    if caw_rows:
        pd.DataFrame(
            caw_rows,
            columns=["reporting_year", "geo_code", "state_ut_name", "metric_type", "normalized_value", "source_table"],
        ).to_csv(processed_dir / "caw_state_totals_official.csv", index=False)

    return logged


def run_registered_ingestion(db: Session, project_root: Optional[Path] = None, force: bool = False) -> IngestionSummary:
    """Execute reproducible ingestion across all official sources in data/documentation/source_registry.json."""
    root = project_root or resolve_project_root()
    registry_path = root / "data" / "documentation" / "source_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    geo_lookup = ensure_geographic_units(db)
    summary = IngestionSummary()

    for src_entry in registry.get("sources", []):
        source = db.scalar(select(DataSource).where(DataSource.slug == src_entry["slug"]))
        if source is None:
            source = DataSource(
                slug=src_entry["slug"],
                official_title=src_entry["official_title"],
                publisher=src_entry["publisher"],
                reporting_period=", ".join(str(y) for y in src_entry.get("years_covered", [])),
                publication_date=src_entry.get("publication_date"),
                download_date=src_entry["download_date"],
                source_url=src_entry["source_url"],
                geographic_coverage=src_entry["geographic_coverage"],
                status="verified_official" if src_entry["reporting_year"] <= 2022 else "partial_official",
                notes=src_entry.get("notes", ""),
            )
            db.add(source)
            db.flush()

        edition_year = int(src_entry["reporting_year"])
        for file_entry in src_entry.get("files", []):
            rel = file_entry["relative_path"]
            ds_key = f"{src_entry['slug']}__{Path(rel).stem.lower()}"
            domain, granularity = _infer_domain_and_granularity(
                file_entry["table_number"], file_entry["ingestion_role"]
            )
            dataset = db.scalar(select(Dataset).where(Dataset.dataset_key == ds_key))
            if dataset is None:
                dataset = Dataset(
                    source_id=source.id,
                    dataset_key=ds_key,
                    table_number=file_entry["table_number"],
                    title=file_entry["title"],
                    crime_domain=domain,
                    granularity=granularity,
                    unit_description=file_entry["unit"],
                    methodology_notes=src_entry.get("notes", ""),
                )
                db.add(dataset)
                db.flush()

            full_path = root / "data" / "raw" / rel
            _ingest_single_file(
                db=db,
                dataset=dataset,
                file_path=full_path,
                table_number=file_entry["table_number"],
                edition_year=edition_year,
                ingestion_role=file_entry["ingestion_role"],
                geo_lookup=geo_lookup,
                summary=summary,
                force=force,
            )

    if summary.versions_processed > 0 or force:
        summary.quality_issues_logged += _refresh_global_audits_and_exports(db, root, geo_lookup)

    db.commit()
    return summary


def ingest_manual_file(
    db: Session,
    file_path: Path,
    table_code: str,
    reporting_year: int,
    source_url: str,
    publisher: str = "National Crime Records Bureau (NCRB), Ministry of Home Affairs, Government of India",
    force: bool = False,
) -> IngestionSummary:
    """Clean manual-import entrypoint for future official Excel/CSV/PDF releases."""
    geo_lookup = ensure_geographic_units(db)
    summary = IngestionSummary()

    slug = f"ncrb-manual-{reporting_year}"
    source = db.scalar(select(DataSource).where(DataSource.slug == slug))
    if source is None:
        source = DataSource(
            slug=slug,
            official_title=f"Manual Official Import — {reporting_year} ({table_code})",
            publisher=publisher,
            reporting_period=str(reporting_year),
            download_date="manual-import",
            source_url=source_url,
            geographic_coverage="Official Manual Import",
            status="verified_official",
            notes=f"Manually imported official file {file_path.name}.",
        )
        db.add(source)
        db.flush()

    ds_key = f"{slug}__{file_path.stem.lower()}"
    dataset = db.scalar(select(Dataset).where(Dataset.dataset_key == ds_key))
    if dataset is None:
        dataset = Dataset(
            source_id=source.id,
            dataset_key=ds_key,
            table_number=table_code,
            title=f"{table_code} ({reporting_year}) Manual Import",
            crime_domain="rape_ipc_376",
            granularity="state_ut",
            unit_description="Official imported statistical table",
        )
        db.add(dataset)
        db.flush()

    _ingest_single_file(
        db=db,
        dataset=dataset,
        file_path=file_path.resolve(),
        table_number=table_code,
        edition_year=reporting_year,
        ingestion_role="manual_import",
        geo_lookup=geo_lookup,
        summary=summary,
        force=force,
    )
    summary.quality_issues_logged += _refresh_global_audits_and_exports(db, resolve_project_root(), geo_lookup)
    db.commit()
    return summary

