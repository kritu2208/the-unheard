import pathlib
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.ingestion.normalizer import parse_numeric_value, resolve_canonical_geo
from app.ingestion.parsers import (
    ParsedCrimeObservation,
    parse_csv_dataset,
    parse_ncrb_pdf,
    parse_table_3a2,
)
from app.ingestion.pipeline import ingest_manual_file, resolve_project_root, run_registered_ingestion
from app.ingestion.validator import validate_parsed_crime_rows
from app.models.records import CrimeStatistic, DatasetVersion, PopulationStatistic


def test_geographic_name_normalization():
    assert resolve_canonical_geo("A & N Islands").code == "AN"
    assert resolve_canonical_geo("D&N Haveli+").code == "DN"
    assert resolve_canonical_geo("Jammu & Kashmir*").code == "JK"
    assert resolve_canonical_geo("Delhi UT").code == "DL"
    assert resolve_canonical_geo("TOTAL ALL INDIA").code == "IN"
    assert resolve_canonical_geo("आंध्र प्रदेश").code == "AP"
    assert resolve_canonical_geo("Nonexistent Province") is None


def test_numeric_parser_preserves_missing_and_strips_footnotes():
    assert parse_numeric_value("3,1516") == (31516.0, False, "3,1516")
    assert parse_numeric_value("3437*") == (3437.0, False, "3437*")
    assert parse_numeric_value("54+") == (54.0, False, "54+")
    val, is_missing, raw = parse_numeric_value("-")
    assert val is None and is_missing is True and raw == "-"
    val2, is_missing2, _ = parse_numeric_value("")
    assert val2 is None and is_missing2 is True


def test_official_excel_and_pdf_parsers():
    root = resolve_project_root()
    p_3a2 = root / "data" / "raw" / "ncrb_2022" / "1701935197TABLE3A2.xlsx"
    res_3a2 = parse_table_3a2(p_3a2, 2022)
    assert res_3a2.status == "completed"
    # Verify All-India Rape (Sec. 376 IPC) keeps Cases (I), Victims (V), Rate (R) distinct
    nat_rape = {
        r.metric_type: r.normalized_value
        for r in res_3a2.crime_rows
        if r.raw_geo_name == "TOTAL ALL INDIA" and r.crime_domain == "rape_ipc_376"
    }
    assert nat_rape["cases_registered"] == 31516.0
    assert nat_rape["victims"] == 31982.0
    assert nat_rape["rate_per_100k_female"] == 4.7

    p_2023 = root / "data" / "raw" / "ncrb_2023" / "9-2023.pdf"
    res_2023 = parse_ncrb_pdf(p_2023, 2023, "pdf_national_caw_2023")
    assert res_2023.status == "partial"
    caw_2023 = {r.metric_type: r.normalized_value for r in res_2023.crime_rows}
    assert caw_2023["cases_registered"] == 448211.0
    assert caw_2023["rate_per_100k_female"] == 66.2


def test_validator_flags_anomalies_without_discarding_valid_rows():
    observations = [
        ParsedCrimeObservation(
            reporting_year=2022,
            raw_geo_name="Rajasthan",
            crime_domain="rape_ipc_376",
            crime_head="Rape (Sec. 376 IPC)",
            sub_category="Total",
            metric_type="cases_registered",
            unit="cases",
            raw_value="-5",
            normalized_value=-5.0,
            denominator_scope="none",
            source_table="TEST",
            source_page_or_row="Row 1",
        ),
        ParsedCrimeObservation(
            reporting_year=2022,
            raw_geo_name="Maharashtra",
            crime_domain="rape_ipc_376",
            crime_head="Rape (Sec. 376 IPC)",
            sub_category="Total",
            metric_type="chargesheet_rate_pct",
            unit="percent",
            raw_value="104.5",
            normalized_value=104.5,
            denominator_scope="cases_disposed",
            source_table="TEST",
            source_page_or_row="Row 2",
        ),
        ParsedCrimeObservation(
            reporting_year=2022,
            raw_geo_name="Kerala",
            crime_domain="rape_ipc_376",
            crime_head="Rape (Sec. 376 IPC)",
            sub_category="Total",
            metric_type="cases_registered",
            unit="cases",
            raw_value="-",
            normalized_value=None,
            denominator_scope="none",
            source_table="TEST",
            source_page_or_row="Row 3",
        ),
        ParsedCrimeObservation(
            reporting_year=2022,
            raw_geo_name="Kerala",
            crime_domain="rape_ipc_376",
            crime_head="Rape (Sec. 376 IPC)",
            sub_category="Total",
            metric_type="cases_registered",
            unit="cases",
            raw_value="-",
            normalized_value=None,
            denominator_scope="none",
            source_table="TEST",
            source_page_or_row="Row 4 (dup)",
        ),
    ]
    validated, issues = validate_parsed_crime_rows(observations, "TEST")
    assert len(validated) == 3  # Negative, invalid percentage, and missing preserved; duplicate skipped
    codes = {i.issue_code for i in issues}
    assert {"NEGATIVE_VALUE", "INVALID_PERCENTAGE", "MISSING_NUMERIC_VALUE", "DUPLICATE_IN_BATCH"} <= codes


def test_idempotent_ingestion_and_manual_csv_import(tmp_path: pathlib.Path):
    db_file = tmp_path / "test_unheard.db"
    eng = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    LocalSession = sessionmaker(autocommit=False, autoflush=False, bind=eng)

    with LocalSession() as db:
        s1 = run_registered_ingestion(db, force=False)
        assert s1.versions_processed == 30
        assert s1.crime_records_written > 6000
        assert s1.population_records_written > 100

        # Second run must skip all 30 versions and write 0 duplicate records
        s2 = run_registered_ingestion(db, force=False)
        assert s2.versions_processed == 0
        assert s2.versions_skipped_duplicate == 30
        assert s2.crime_records_written == 0

        # Manual CSV import workflow verification
        csv_path = tmp_path / "manual_2023.csv"
        csv_path.write_text(
            "State/UT,year,value,crime_head,crime_domain,metric_type,unit\n"
            "Rajasthan,2024,5000,Rape (BNS Sec. 63),rape_ipc_376,cases_registered,cases\n",
            encoding="utf-8",
        )
        parsed = parse_csv_dataset(csv_path, default_year=2024, table_code="MANUAL TEST")
        assert len(parsed.crime_rows) == 1
        ms = ingest_manual_file(
            db,
            file_path=csv_path,
            table_code="MANUAL TEST",
            reporting_year=2024,
            source_url="https://www.ncrb.gov.in/",
        )
        assert ms.versions_processed == 1
        assert ms.crime_records_written == 1
        assert db.scalar(select(func.count(DatasetVersion.id))) == 31
        assert db.scalar(select(func.count(PopulationStatistic.id))) == s1.population_records_written
        assert db.scalar(select(func.count(CrimeStatistic.id))) == s1.crime_records_written + 1
    eng.dispose()

