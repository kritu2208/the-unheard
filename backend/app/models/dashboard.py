from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DatasetSource(Base):
    """Official statistical source registry entry."""

    __tablename__ = "dataset_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    reporting_period: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    granularity: Mapped[str] = mapped_column(String(120), nullable=False)
    definitions_summary: Mapped[str] = mapped_column(Text, nullable=False)
    missing_data_notes: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class DemoNationalYear(Base):
    """Explicitly flagged DEMO DATA annual series for Phase 1 dashboard testing."""

    __tablename__ = "demo_national_years"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    demo_reported_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    demo_rate_per_100k: Mapped[float] = mapped_column(Float, nullable=False)
    demo_charge_sheet_pct: Mapped[float] = mapped_column(Float, nullable=False)
    demo_conviction_pct: Mapped[float] = mapped_column(Float, nullable=False)
    statutory_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DemoStateObservation(Base):
    """Explicitly flagged DEMO DATA state/UT series for Phase 1 geographic & export controls."""

    __tablename__ = "demo_state_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    state_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    state_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    region_zone: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    demo_reported_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    demo_rate_per_100k: Mapped[float] = mapped_column(Float, nullable=False)
    demo_charge_sheet_pct: Mapped[float] = mapped_column(Float, nullable=False)
    demo_conviction_pct: Mapped[float] = mapped_column(Float, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

