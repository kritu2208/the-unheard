import argparse
from pathlib import Path

from app.database.session import SessionLocal, init_db
from app.ingestion.pipeline import ingest_manual_file, run_registered_ingestion


def main() -> None:
    parser = argparse.ArgumentParser(description="THE UNHEARD — Official NCRB Data Ingestion Pipeline")
    parser.add_argument("--force", action="store_true", help="Re-ingest files even if SHA-256 checksum already exists.")
    parser.add_argument("--manual-file", type=str, default=None, help="Path to an official CSV/Excel file to manually import.")
    parser.add_argument("--table-code", type=str, default="TABLE 3A.2", help="Official table reference code for manual import.")
    parser.add_argument("--year", type=int, default=2023, help="Reporting year for manual import.")
    parser.add_argument("--source-url", type=str, default="https://www.ncrb.gov.in/", help="Official URL for manual import.")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        if args.manual_file:
            summary = ingest_manual_file(
                db=db,
                file_path=Path(args.manual_file),
                table_code=args.table_code,
                reporting_year=args.year,
                source_url=args.source_url,
                force=args.force,
            )
        else:
            summary = run_registered_ingestion(db=db, force=args.force)

    print(
        f"Ingestion complete: versions_processed={summary.versions_processed}, "
        f"versions_skipped_duplicate={summary.versions_skipped_duplicate}, "
        f"crime_records_written={summary.crime_records_written}, "
        f"population_records_written={summary.population_records_written}, "
        f"quality_issues_logged={summary.quality_issues_logged}"
    )


if __name__ == "__main__":
    main()

