from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DataSource(Base):
    """Official publisher/edition source registry record."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    official_title: Mapped[str] = mapped_column(String(300), nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    reporting_period: Mapped[str] = mapped_column(String(80), nullable=False)
    publication_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    download_date: Mapped[str] = mapped_column(String(40), nullable=False)
    source_url: Mapped[str] = mapped_column(String(600), nullable=False)
    geographic_coverage: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="verified_official")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class Dataset(Base):
    """Specific official table or report file mapped under a DataSource."""

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False, index=True)
    dataset_key: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    table_number: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    crime_domain: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    granularity: Mapped[str] = mapped_column(String(40), nullable=False)
    unit_description: Mapped[str] = mapped_column(String(300), nullable=False)
    methodology_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)

    source: Mapped["DataSource"] = relationship(back_populates="datasets")
    versions: Mapped[list["DatasetVersion"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class DatasetVersion(Base):
    """Immutable provenance & SHA-256 fingerprint for an ingested file version."""

    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "file_sha256", "reporting_year", name="uq_dataset_version_hash_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False, index=True)
    version_label: Mapped[str] = mapped_column(String(60), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ingestion_status: Mapped[str] = mapped_column(String(40), nullable=False, default="completed")
    extraction_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)

    dataset: Mapped["Dataset"] = relationship(back_populates="versions")
    crime_statistics: Mapped[list["CrimeStatistic"]] = relationship(
        back_populates="dataset_version", cascade="all, delete-orphan"
    )
    population_statistics: Mapped[list["PopulationStatistic"]] = relationship(
        back_populates="dataset_version", cascade="all, delete-orphan"
    )
    quality_issues: Mapped[list["DataQualityIssue"]] = relationship(
        back_populates="dataset_version", cascade="all, delete-orphan"
    )


class GeographicUnit(Base):
    """Canonical All-India, State, and Union Territory reference entity."""

    __tablename__ = "geographic_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    unit_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    region_zone: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    aliases_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    boundary_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    active_from_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_to_year: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CrimeStatistic(Base):
    """Normalized, traceable official crime statistic observation."""

    __tablename__ = "crime_statistics"
    __table_args__ = (
        Index("ix_crime_lookup", "reporting_year", "crime_domain", "metric_type", "geographic_unit_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False, index=True)
    geographic_unit_id: Mapped[int] = mapped_column(ForeignKey("geographic_units.id"), nullable=False, index=True)
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    crime_domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    crime_head: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    sub_category: Mapped[str] = mapped_column(String(140), nullable=False, default="Total")
    metric_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_geo_name: Mapped[str] = mapped_column(String(160), nullable=False)
    raw_value: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    denominator_scope: Mapped[str] = mapped_column(String(64), nullable=False, default="none")
    source_table: Mapped[str] = mapped_column(String(80), nullable=False)
    source_page_or_row: Mapped[str] = mapped_column(String(120), nullable=False)
    is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="verified", index=True)
    validation_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    record_fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    dataset_version: Mapped["DatasetVersion"] = relationship(back_populates="crime_statistics")
    geographic_unit: Mapped["GeographicUnit"] = relationship()


class PopulationStatistic(Base):
    """Official mid-year projected population denominator (explicitly scoped female vs total)."""

    __tablename__ = "population_statistics"
    __table_args__ = (
        Index("ix_pop_lookup", "reporting_year", "denominator_scope", "geographic_unit_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False, index=True)
    geographic_unit_id: Mapped[int] = mapped_column(ForeignKey("geographic_units.id"), nullable=False, index=True)
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    denominator_scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    population_lakhs: Mapped[float] = mapped_column(Float, nullable=False)
    raw_geo_name: Mapped[str] = mapped_column(String(160), nullable=False)
    raw_value: Mapped[str] = mapped_column(String(80), nullable=False)
    source_table: Mapped[str] = mapped_column(String(80), nullable=False)
    source_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="verified")
    record_fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    dataset_version: Mapped["DatasetVersion"] = relationship(back_populates="population_statistics")
    geographic_unit: Mapped["GeographicUnit"] = relationship()


class DataQualityIssue(Base):
    """Automated anomaly, provenance, boundary, and validation audit record."""

    __tablename__ = "data_quality_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataset_versions.id"), nullable=True, index=True
    )
    geographic_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("geographic_units.id"), nullable=True, index=True
    )
    reporting_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    issue_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str] = mapped_column(String(80), nullable=False, default="PIPELINE")
    affected_record_ref: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)

    dataset_version: Mapped["DatasetVersion | None"] = relationship(back_populates="quality_issues")
    geographic_unit: Mapped["GeographicUnit | None"] = relationship()

