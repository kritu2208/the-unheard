import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import openpyxl
import pandas as pd
import pypdf

from app.ingestion.normalizer import parse_numeric_value, resolve_canonical_geo


@dataclass
class ParsedCrimeObservation:
    reporting_year: int
    raw_geo_name: str
    crime_domain: str
    crime_head: str
    sub_category: str
    metric_type: str
    unit: str
    raw_value: str
    normalized_value: Optional[float]
    denominator_scope: str
    source_table: str
    source_page_or_row: str
    is_estimated: bool = False


@dataclass
class ParsedPopulationObservation:
    reporting_year: int
    raw_geo_name: str
    denominator_scope: str  # "female" | "total"
    raw_value: str
    population_lakhs: Optional[float]
    source_table: str
    source_notes: str


@dataclass
class ParseResult:
    table_code: str
    reporting_year: int
    crime_rows: List[ParsedCrimeObservation] = field(default_factory=list)
    population_rows: List[ParsedPopulationObservation] = field(default_factory=list)
    extraction_notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    status: str = "completed"


def _is_footer_or_section_marker(label: object) -> bool:
    if label is None:
        return True
    s = str(label).strip()
    if not s:
        return True
    upper = s.upper()
    if upper in {"STATES:", "STATE:", "UNION TERRITORIES:", "UNION TERRITORY:", "UT:", "UTS:", "SL", "STATE/UT"}:
        return True
    if s.startswith("[") or s.startswith("●") or s.startswith("'") or "TABLE 3A" in upper:
        return True
    if "AS PER DATA" in upper or "MAY NOT BE COMPARED" in upper or "I=" in upper:
        return True
    return False


def _load_sheet_rows(file_path: Path) -> List[List[object]]:
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    try:
        ws = wb[wb.sheetnames[0]]
        return [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def _detect_year_from_header(rows: Sequence[Sequence[object]], fallback_year: int) -> int:
    for r in rows[:4]:
        for cell in r[:8]:
            if cell is None:
                continue
            m = re.search(r"(20\d{2})\s*$", str(cell).strip())
            if m:
                return int(m.group(1))
    return fallback_year


def parse_table_3a1(file_path: Path, edition_year: int) -> ParseResult:
    """Parse TABLE 3A.1: multi-year Total Crime Against Women + Projected Female Population."""
    rows = _load_sheet_rows(file_path)
    result = ParseResult(table_code="TABLE 3A.1", reporting_year=edition_year)

    header_idx = next(
        (i for i, r in enumerate(rows[:8]) if len(r) > 1 and str(r[1]).strip().lower() == "state/ut"),
        2,
    )
    hdr = rows[header_idx]
    year_cols: List[Tuple[int, int]] = []
    pop_col: Optional[int] = None
    rate_col: Optional[int] = None
    cs_col: Optional[int] = None

    for idx, cell in enumerate(hdr):
        text = str(cell or "").strip()
        if re.fullmatch(r"20\d{2}", text):
            year_cols.append((idx, int(text)))
        elif "population" in text.lower():
            pop_col = idx
        elif "rate of total crime" in text.lower():
            rate_col = idx
        elif "chargesheeting rate" in text.lower():
            cs_col = idx

    for row_num, r in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
        raw_geo = r[1] if len(r) > 1 else None
        if _is_footer_or_section_marker(raw_geo):
            continue
        raw_geo_str = str(raw_geo).strip()

        for col_idx, yr in year_cols:
            if col_idx >= len(r):
                continue
            val, is_missing, raw_str = parse_numeric_value(r[col_idx])
            if is_missing and raw_str == "":
                continue
            result.crime_rows.append(
                ParsedCrimeObservation(
                    reporting_year=yr,
                    raw_geo_name=raw_geo_str,
                    crime_domain="caw_total",
                    crime_head="Total Crime against Women (IPC+SLL)",
                    sub_category="Total",
                    metric_type="cases_registered",
                    unit="cases",
                    raw_value=raw_str,
                    normalized_value=val,
                    denominator_scope="none",
                    source_table=f"TABLE 3A.1 ({edition_year} edition)",
                    source_page_or_row=f"Row {row_num} / Col {col_idx + 1}",
                )
            )

        if pop_col is not None and pop_col < len(r):
            pval, p_missing, praw = parse_numeric_value(r[pop_col])
            if not p_missing and pval is not None:
                result.population_rows.append(
                    ParsedPopulationObservation(
                        reporting_year=edition_year,
                        raw_geo_name=raw_geo_str,
                        denominator_scope="female",
                        raw_value=praw,
                        population_lakhs=pval,
                        source_table=f"TABLE 3A.1 ({edition_year} edition)",
                        source_notes="Mid-Year Projected Female Population (in Lakhs) published by NCRB from RGI/MoHFW Technical Group projections.",
                    )
                )

        if rate_col is not None and rate_col < len(r):
            rval, r_missing, rraw = parse_numeric_value(r[rate_col])
            if not r_missing:
                result.crime_rows.append(
                    ParsedCrimeObservation(
                        reporting_year=edition_year,
                        raw_geo_name=raw_geo_str,
                        crime_domain="caw_total",
                        crime_head="Total Crime against Women (IPC+SLL)",
                        sub_category="Total",
                        metric_type="rate_per_100k_female",
                        unit="rate_per_lakh_female_population",
                        raw_value=rraw,
                        normalized_value=rval,
                        denominator_scope="female_projected",
                        source_table=f"TABLE 3A.1 ({edition_year} edition)",
                        source_page_or_row=f"Row {row_num} / Rate",
                    )
                )

        if cs_col is not None and cs_col < len(r):
            cval, c_missing, craw = parse_numeric_value(r[cs_col])
            if not c_missing:
                result.crime_rows.append(
                    ParsedCrimeObservation(
                        reporting_year=edition_year,
                        raw_geo_name=raw_geo_str,
                        crime_domain="caw_total",
                        crime_head="Total Crime against Women (IPC+SLL)",
                        sub_category="Total",
                        metric_type="chargesheet_rate_pct",
                        unit="percent",
                        raw_value=craw,
                        normalized_value=cval,
                        denominator_scope="cases_disposed",
                        source_table=f"TABLE 3A.1 ({edition_year} edition)",
                        source_page_or_row=f"Row {row_num} / Chargesheeting Rate",
                    )
                )

    result.extraction_notes.append(
        f"Parsed {len(result.crime_rows)} CAW metrics and {len(result.population_rows)} female population rows across years {[y for _, y in year_cols]}."
    )
    return result


def parse_table_3a2(file_path: Path, edition_year: int) -> ParseResult:
    """Parse wide multi-header TABLE 3A.2 keeping Cases (I), Female Victims (V), and Rate (R) distinct."""
    rows = _load_sheet_rows(file_path)
    result = ParseResult(table_code="TABLE 3A.2", reporting_year=edition_year)

    sub_row_idx = next(
        (i for i, r in enumerate(rows[:9]) if "I" in [str(c).strip() for c in r[:10] if c is not None]),
        5,
    )
    top_headers = rows[2:sub_row_idx]
    ivr_row = rows[sub_row_idx]

    # Map every Crime Head block header -> canonical crime_head & crime_domain (most specific first)
    target_heads: List[Tuple[str, str, str]] = [
        ("murder with rape/gang rape", "Murder with Rape/Gang Rape", "murder_with_rape"),
        ("attempt to commit rape (total)", "Attempt to Commit Rape (Sec. 376/511 IPC)", "attempt_to_rape"),
        ("rape (sec.376 ipc)", "Rape (Sec. 376 IPC)", "rape_ipc_376"),
        ("child rape (sec 4 & 6", "Child Rape (POCSO Sec. 4 & 6 / Sec. 376 IPC)", "pocso_child_rape"),
        ("total ipc crimes against women", "Total IPC Crimes against Women", "caw_ipc_total"),
        ("total sll crimes against women", "Total SLL Crimes against Women", "caw_sll_total"),
        ("total crime against women (ipc+sll)", "Total Crime against Women (IPC+SLL)", "caw_total"),
    ]

    discovered_blocks: List[Tuple[int, str, str]] = []
    max_cols = len(ivr_row)
    for col in range(max_cols):
        parts = [str(h[col]).replace("\n", " ").strip() for h in top_headers if col < len(h) and h[col] is not None]
        if not parts:
            continue
        combined = " ".join(parts).lower()
        combined = re.sub(r"\s+", " ", combined)
        for pattern, canonical_head, domain in target_heads:
            if pattern in combined:
                # Verify I, V, R columns exist
                ivr_slice = [str(ivr_row[col + offset] or "").strip().upper() for offset in range(3) if col + offset < max_cols]
                if ivr_slice == ["I", "V", "R"]:
                    discovered_blocks.append((col, canonical_head, domain))
                break

    if not discovered_blocks:
        result.status = "failed"
        result.warnings.append("Failed to locate Rape/CAW I-V-R column blocks in TABLE 3A.2.")
        return result

    for row_num, r in enumerate(rows[sub_row_idx + 2 :], start=sub_row_idx + 3):
        raw_geo = r[1] if len(r) > 1 else None
        if _is_footer_or_section_marker(raw_geo):
            continue
        raw_geo_str = str(raw_geo).strip()

        for col_start, canonical_head, domain in discovered_blocks:
            triplets = [
                (0, "cases_registered", "cases", "none"),
                (1, "victims", "female_victims", "none"),
                (2, "rate_per_100k_female", "rate_per_lakh_female_population", "female_projected"),
            ]
            for offset, metric_type, unit, denom in triplets:
                cidx = col_start + offset
                val_raw = r[cidx] if cidx < len(r) else None
                val, is_missing, raw_str = parse_numeric_value(val_raw)
                if is_missing and raw_str == "":
                    continue
                result.crime_rows.append(
                    ParsedCrimeObservation(
                        reporting_year=edition_year,
                        raw_geo_name=raw_geo_str,
                        crime_domain=domain,
                        crime_head=canonical_head,
                        sub_category="Total",
                        metric_type=metric_type,
                        unit=unit,
                        raw_value=raw_str,
                        normalized_value=val,
                        denominator_scope=denom,
                        source_table=f"TABLE 3A.2 ({edition_year} edition)",
                        source_page_or_row=f"Row {row_num} / Col {cidx + 1}",
                    )
                )

    result.extraction_notes.append(
        f"Discovered {len(discovered_blocks)} target crime-head I/V/R blocks; extracted {len(result.crime_rows)} normalized observations."
    )
    return result


def parse_table_3a3(file_path: Path, edition_year: int) -> ParseResult:
    """Parse TABLE 3A.3: Victims of Rape by Age Group (State/UT-wise)."""
    rows = _load_sheet_rows(file_path)
    result = ParseResult(table_code="TABLE 3A.3", reporting_year=edition_year)

    col_idx_row = next(
        (i for i, r in enumerate(rows[:8]) if str(r[0] or "").strip() == "[1]"),
        4,
    )
    # Use NCRB's numbered columns [3]..[14] (0-indexed cols 2..13) when header structure matches
    age_columns: List[Tuple[int, str, str, str]] = [
        (2, "Cases Reported", "cases_registered", "cases"),
        (3, "Child: Below 6 Years", "victims", "female_victims"),
        (4, "Child: 6 to 12 Years", "victims", "female_victims"),
        (5, "Child: 12 to 16 Years", "victims", "female_victims"),
        (6, "Child: 16 to 18 Years", "victims", "female_victims"),
        (7, "Child Victims Subtotal (Below 18 Years)", "victims", "female_victims"),
        (8, "Adult: 18 to 30 Years", "victims", "female_victims"),
        (9, "Adult: 30 to 45 Years", "victims", "female_victims"),
        (10, "Adult: 45 to 60 Years", "victims", "female_victims"),
        (11, "Adult: 60 Years & Above", "victims", "female_victims"),
        (12, "Adult Victims Subtotal (18+ Years)", "victims", "female_victims"),
        (13, "Total Rape Victims (All Ages)", "victims", "female_victims"),
    ]

    for row_num, r in enumerate(rows[col_idx_row + 1 :], start=col_idx_row + 2):
        raw_geo = r[1] if len(r) > 1 else None
        if _is_footer_or_section_marker(raw_geo):
            continue
        raw_geo_str = str(raw_geo).strip()

        for cidx, sub_cat, metric_type, unit in age_columns:
            if cidx >= len(r):
                continue
            val, is_missing, raw_str = parse_numeric_value(r[cidx])
            if is_missing and raw_str == "":
                continue
            result.crime_rows.append(
                ParsedCrimeObservation(
                    reporting_year=edition_year,
                    raw_geo_name=raw_geo_str,
                    crime_domain="rape_age_groups",
                    crime_head="Rape (Sec. 376 IPC)",
                    sub_category=sub_cat,
                    metric_type=metric_type,
                    unit=unit,
                    raw_value=raw_str,
                    normalized_value=val,
                    denominator_scope="none",
                    source_table=f"TABLE 3A.3 ({edition_year} edition)",
                    source_page_or_row=f"Row {row_num} / Col {cidx + 1}",
                )
            )

    result.extraction_notes.append(f"Extracted {len(result.crime_rows)} Rape victim age-group observations.")
    return result


def parse_table_3a4(file_path: Path, edition_year: int) -> ParseResult:
    """Parse TABLE 3A.4: Offenders Relation to Victims of Rape (Sec. 376 IPC)."""
    rows = _load_sheet_rows(file_path)
    result = ParseResult(table_code="TABLE 3A.4", reporting_year=edition_year)

    col_idx_row = next(
        (i for i, r in enumerate(rows[:8]) if str(r[0] or "").strip() == "[1]"),
        4,
    )
    relation_cols: List[Tuple[int, str, str, str, str]] = [
        (2, "Offender Known to Victim (Total)", "cases_registered", "cases", "none"),
        (3, "Family Members", "cases_registered", "cases", "none"),
        (4, "Friends / Online-Friends / Live-in Partners / Separated Husband", "cases_registered", "cases", "none"),
        (5, "Family Friends / Neighbours / Employer / Other Known Persons", "cases_registered", "cases", "none"),
        (6, "Offenders Unknown or Not Identified", "cases_registered", "cases", "none"),
        (7, "Total Rape Cases (Known + Unknown)", "cases_registered", "cases", "none"),
        (8, "Share of Known Offender Cases (%)", "share_pct", "percent", "all_rape_cases"),
    ]

    for row_num, r in enumerate(rows[col_idx_row + 1 :], start=col_idx_row + 2):
        raw_geo = r[1] if len(r) > 1 else None
        if _is_footer_or_section_marker(raw_geo):
            continue
        raw_geo_str = str(raw_geo).strip()

        for cidx, sub_cat, metric_type, unit, denom in relation_cols:
            if cidx >= len(r):
                continue
            val, is_missing, raw_str = parse_numeric_value(r[cidx])
            if is_missing and raw_str == "":
                continue
            result.crime_rows.append(
                ParsedCrimeObservation(
                    reporting_year=edition_year,
                    raw_geo_name=raw_geo_str,
                    crime_domain="rape_offender_relation",
                    crime_head="Rape (Sec. 376 IPC)",
                    sub_category=sub_cat,
                    metric_type=metric_type,
                    unit=unit,
                    raw_value=raw_str,
                    normalized_value=val,
                    denominator_scope=denom,
                    source_table=f"TABLE 3A.4 ({edition_year} edition)",
                    source_page_or_row=f"Row {row_num} / Col {cidx + 1}",
                )
            )

    result.extraction_notes.append(f"Extracted {len(result.crime_rows)} offender-relationship observations.")
    return result


def parse_table_3a5_or_3a7(file_path: Path, edition_year: int, table_code: str) -> ParseResult:
    """Parse national crime-head-wise Police Disposal (3A.5) or Court Disposal (3A.7)."""
    rows = _load_sheet_rows(file_path)
    result = ParseResult(table_code=table_code, reporting_year=edition_year)

    col_idx_row = next(
        (i for i, r in enumerate(rows[:8]) if "[1]" in [str(c or "").strip() for c in r[:5]]),
        3,
    )
    # Map NCRB official bracket column numbers -> metric specs so horizontal splits resolve consistently
    col_num_to_col_idx: Dict[str, int] = {}
    for cidx, cell in enumerate(rows[col_idx_row]):
        token = str(cell or "").strip()
        if re.fullmatch(r"\[\d+\]", token) and token not in ("[1]", "[2]"):
            col_num_to_col_idx[token] = cidx

    if table_code == "TABLE 3A.5":
        domain = "rape_national_police_disposal"
        specs = [
            ("[3]", "Total", "cases_pending_prev_year", "cases", "none"),
            ("[4]", "Total", "cases_reported_for_investigation", "cases", "none"),
            ("[6]", "Total", "cases_for_investigation", "cases", "none"),
            ("[18]", "Total", "cases_chargesheeted", "cases", "none"),
            ("[19]", "Total", "cases_disposed_police", "cases", "none"),
            ("[22]", "Total", "cases_pending_investigation", "cases", "none"),
            ("[23]", "Total", "chargesheet_rate_pct", "percent", "cases_disposed"),
            ("[24]", "Total", "investigation_pendency_pct", "percent", "cases_for_investigation"),
        ]
    else:
        domain = "rape_national_court_disposal"
        specs = [
            ("[3]", "Total", "cases_pending_trial_prev_year", "cases", "none"),
            ("[4]", "Total", "cases_sent_for_trial", "cases", "none"),
            ("[5]", "Total", "cases_for_trial", "cases", "none"),
            ("[15]", "Total", "cases_convicted", "cases", "none"),
            ("[16]", "Total", "cases_discharged", "cases", "none"),
            ("[17]", "Total", "cases_acquitted", "cases", "none"),
            ("[18]", "Total", "trials_completed", "cases", "none"),
            ("[19]", "Total", "cases_disposed_courts", "cases", "none"),
            ("[20]", "Total", "cases_pending_trial", "cases", "none"),
            ("[21]", "Total", "conviction_rate_pct", "percent", "trials_completed"),
            ("[22]", "Total", "trial_pendency_pct", "percent", "cases_for_trial"),
        ]

    target_crime_heads = {
        "rape": "Rape (Sec. 376 IPC)",
        "attempt to commit rape": "Attempt to Commit Rape (Sec. 376/511 IPC)",
        "murder with rape/gang rape": "Murder with Rape/Gang Rape",
        "total crime against women": "Total Crime against Women (IPC+SLL)",
    }

    for row_num, r in enumerate(rows[col_idx_row + 1 :], start=col_idx_row + 2):
        head_raw = str(r[1] or "").strip() if len(r) > 1 else ""
        head_key = re.sub(r"\s+", " ", head_raw).lower()
        canonical_head = target_crime_heads.get(head_key)
        if not canonical_head:
            continue

        row_domain = domain if canonical_head != "Total Crime against Women (IPC+SLL)" else f"caw_national_{'police' if table_code == 'TABLE 3A.5' else 'court'}_disposal"
        for bracket, sub_cat, metric_type, unit, denom in specs:
            cidx = col_num_to_col_idx.get(bracket)
            if cidx is None or cidx >= len(r):
                continue
            val, is_missing, raw_str = parse_numeric_value(r[cidx])
            if is_missing and raw_str == "":
                continue
            result.crime_rows.append(
                ParsedCrimeObservation(
                    reporting_year=edition_year,
                    raw_geo_name="TOTAL ALL INDIA",
                    crime_domain=row_domain,
                    crime_head=canonical_head,
                    sub_category=sub_cat,
                    metric_type=metric_type,
                    unit=unit,
                    raw_value=raw_str,
                    normalized_value=val,
                    denominator_scope=denom,
                    source_table=f"{table_code} ({edition_year} edition)",
                    source_page_or_row=f"Row {row_num} / {head_raw} / Col {bracket}",
                )
            )

    result.extraction_notes.append(f"Extracted {len(result.crime_rows)} national crime-head disposal observations.")
    return result


def parse_table_3a6_or_3a8(file_path: Path, edition_year: int, table_code: str) -> ParseResult:
    """Parse State/UT-wise Disposal of Total Crime against Women (explicitly tagged CAW-only)."""
    rows = _load_sheet_rows(file_path)
    result = ParseResult(table_code=table_code, reporting_year=edition_year)

    col_idx_row = next(
        (i for i, r in enumerate(rows[:8]) if "[1]" in [str(c or "").strip() for c in r[:5]]),
        3,
    )
    col_num_to_col_idx: Dict[str, int] = {}
    for cidx, cell in enumerate(rows[col_idx_row]):
        token = str(cell or "").strip()
        if re.fullmatch(r"\[\d+\]", token) and token not in ("[1]", "[2]"):
            col_num_to_col_idx[token] = cidx

    if table_code == "TABLE 3A.6":
        domain = "caw_state_police_disposal"
        specs = [
            ("[6]", "Total CAW (Not Rape-only)", "cases_for_investigation", "cases", "none"),
            ("[18]", "Total CAW (Not Rape-only)", "cases_chargesheeted", "cases", "none"),
            ("[23]", "Total CAW (Not Rape-only)", "chargesheet_rate_pct", "percent", "cases_disposed"),
            ("[24]", "Total CAW (Not Rape-only)", "investigation_pendency_pct", "percent", "cases_for_investigation"),
        ]
    else:
        domain = "caw_state_court_disposal"
        specs = [
            ("[5]", "Total CAW (Not Rape-only)", "cases_for_trial", "cases", "none"),
            ("[15]", "Total CAW (Not Rape-only)", "cases_convicted", "cases", "none"),
            ("[18]", "Total CAW (Not Rape-only)", "trials_completed", "cases", "none"),
            ("[21]", "Total CAW (Not Rape-only)", "conviction_rate_pct", "percent", "trials_completed"),
            ("[22]", "Total CAW (Not Rape-only)", "trial_pendency_pct", "percent", "cases_for_trial"),
        ]

    for row_num, r in enumerate(rows[col_idx_row + 1 :], start=col_idx_row + 2):
        raw_geo = r[1] if len(r) > 1 else None
        if _is_footer_or_section_marker(raw_geo):
            continue
        raw_geo_str = str(raw_geo).strip()

        for bracket, sub_cat, metric_type, unit, denom in specs:
            cidx = col_num_to_col_idx.get(bracket)
            if cidx is None or cidx >= len(r):
                continue
            val, is_missing, raw_str = parse_numeric_value(r[cidx])
            if is_missing and raw_str == "":
                continue
            result.crime_rows.append(
                ParsedCrimeObservation(
                    reporting_year=edition_year,
                    raw_geo_name=raw_geo_str,
                    crime_domain=domain,
                    crime_head="Total Crime against Women (IPC+SLL)",
                    sub_category=sub_cat,
                    metric_type=metric_type,
                    unit=unit,
                    raw_value=raw_str,
                    normalized_value=val,
                    denominator_scope=denom,
                    source_table=f"{table_code} ({edition_year} edition)",
                    source_page_or_row=f"Row {row_num} / Col {bracket}",
                )
            )

    result.extraction_notes.append(
        f"Extracted {len(result.crime_rows)} State/UT Total CAW disposal rows (strictly scoped to CAW, not Sec. 376 Rape alone)."
    )
    return result


def parse_table_3a11(file_path: Path, edition_year: int) -> ParseResult:
    """Parse TABLE 3A.11: Section-wise Cases Registered under Rape."""
    rows = _load_sheet_rows(file_path)
    result = ParseResult(table_code="TABLE 3A.11", reporting_year=edition_year)

    col_idx_row = next(
        (i for i, r in enumerate(rows[:8]) if "[1]" in [str(c or "").strip() for c in r[:5]]),
        4,
    )
    col_num_to_col_idx: Dict[str, int] = {}
    for cidx, cell in enumerate(rows[col_idx_row]):
        token = str(cell or "").strip()
        if re.fullmatch(r"\[\d+\]", token) and token not in ("[1]", "[2]"):
            col_num_to_col_idx[token] = cidx

    specs = [
        ("[3]", "Sec. 376 & 376(1) Standard"),
        ("[4]", "Custodial Rape Total Sec. 376(2)(a-e)"),
        ("[10]", "Other Than Custodial Total Sec. 376(2)"),
        ("[20]", "Girl Below 16 Years Sec. 376(3)"),
        ("[23]", "Girl Below 12 Years Sec. 376(AB)"),
        ("[25]", "Gang Rape Sec. 376(D)"),
        ("[26]", "Gang Rape Girl Below 16 Sec. 376(DA)"),
        ("[27]", "Gang Rape Girl Below 12 Sec. 376(DB)"),
        ("[29]", "Total Rape (Sec. 376 IPC)"),
    ]

    for row_num, r in enumerate(rows[col_idx_row + 1 :], start=col_idx_row + 2):
        raw_geo = r[1] if len(r) > 1 else None
        if _is_footer_or_section_marker(raw_geo):
            continue
        raw_geo_str = str(raw_geo).strip()
        for bracket, sub_cat in specs:
            cidx = col_num_to_col_idx.get(bracket)
            if cidx is None or cidx >= len(r):
                continue
            val, is_missing, raw_str = parse_numeric_value(r[cidx])
            if is_missing and raw_str == "":
                continue
            result.crime_rows.append(
                ParsedCrimeObservation(
                    reporting_year=edition_year,
                    raw_geo_name=raw_geo_str,
                    crime_domain="rape_section_wise",
                    crime_head="Rape (Sec. 376 IPC)",
                    sub_category=sub_cat,
                    metric_type="cases_registered",
                    unit="cases",
                    raw_value=raw_str,
                    normalized_value=val,
                    denominator_scope="none",
                    source_table=f"TABLE 3A.11 ({edition_year} edition)",
                    source_page_or_row=f"Row {row_num} / Col {bracket}",
                )
            )

    result.extraction_notes.append(f"Extracted {len(result.crime_rows)} section-wise Rape case rows.")
    return result


def parse_ncrb_pdf(file_path: Path, edition_year: int, ingestion_role: str) -> ParseResult:
    """Extract verifiable facts from official NCRB PDFs and record parsing boundaries transparently."""
    reader = pypdf.PdfReader(str(file_path))
    full_text = "\n".join((page.extract_text() or "") for page in reader.pages)

    if ingestion_role == "pdf_national_caw_2023":
        result = ParseResult(table_code="9-2023.pdf", reporting_year=2023)
        compact = re.sub(r"\s+", " ", full_text)
        # Anchor directly to section quoting Table 3A.1 ("3ए.1") and Table 3A.2 ("3ए.2")
        m_caw = re.search(r"(\d,\d{2},\d{3})\s+मामले\s+दर्ष\s+हुए[^[]{0,120}\[ताकलिा\s*[–-]\s*3ए\.1", compact)
        if m_caw:
            val, _, raw_s = parse_numeric_value(m_caw.group(1))
            if val is not None:
                result.crime_rows.append(
                    ParsedCrimeObservation(
                        reporting_year=2023,
                        raw_geo_name="TOTAL ALL INDIA",
                        crime_domain="caw_total",
                        crime_head="Total Crime against Women (IPC+SLL)",
                        sub_category="Total",
                        metric_type="cases_registered",
                        unit="cases",
                        raw_value=raw_s,
                        normalized_value=val,
                        denominator_scope="none",
                        source_table="NCRB 2023 Snapshots (9-2023.pdf, citing Table 3A.1)",
                        source_page_or_row="Page 2",
                    )
                )
        m_rate = re.search(r"66\.4[^[]{0,60}?2023\s*में\s*(\d+\.\d+)[^[]{0,40}\[ताकलिा\s*[–-]\s*3ए\.2", compact)
        if m_rate:
            rval, _, rraw = parse_numeric_value(m_rate.group(1))
            if rval is not None:
                result.crime_rows.append(
                    ParsedCrimeObservation(
                        reporting_year=2023,
                        raw_geo_name="TOTAL ALL INDIA",
                        crime_domain="caw_total",
                        crime_head="Total Crime against Women (IPC+SLL)",
                        sub_category="Total",
                        metric_type="rate_per_100k_female",
                        unit="rate_per_lakh_female_population",
                        raw_value=rraw,
                        normalized_value=rval,
                        denominator_scope="female_projected",
                        source_table="NCRB 2023 Snapshots (9-2023.pdf, citing Table 3A.2)",
                        source_page_or_row="Page 3",
                    )
                )
        result.warnings.append(
            "9-2023.pdf contains National Total Crime Against Women (448,211) and Female Rate (66.2), "
            "but does NOT disaggregate Sec. 376 Rape or State/UT-wise Rape counts. Individual 2023 Table 3A Excel sheets are not yet published on ncrb.gov.in."
        )
        result.status = "partial"
        return result

    if ingestion_role == "pdf_total_population":
        result = ParseResult(table_code="6Population2023.pdf", reporting_year=2023)
        # Match "1 आंध्र प्रदेश 532.17" pairs from Hindi table
        pair_pattern = re.compile(r"(?:^|\s)\d{1,2}\s+([^\d\n]{3,35}?)\s+(\d{1,4}\.\d{2})(?=\s|$)")
        for match in pair_pattern.finditer(full_text.replace("\xa0", " ")):
            raw_state = re.sub(r"\s+", " ", match.group(1)).strip()
            pop_val, is_missing, raw_pop = parse_numeric_value(match.group(2))
            if is_missing or pop_val is None:
                continue
            if resolve_canonical_geo(raw_state):
                result.population_rows.append(
                    ParsedPopulationObservation(
                        reporting_year=2023,
                        raw_geo_name=raw_state,
                        denominator_scope="total",
                        raw_value=raw_pop,
                        population_lakhs=pop_val,
                        source_table="NCRB 2023 Prelims p.viii (6Population2023.pdf)",
                        source_notes="Total Projected Mid-Year Population (both sexes, Lakhs). Not usable as female-only crime denominator.",
                    )
                )
        result.extraction_notes.append(
            f"Extracted {len(result.population_rows)} 2023 State/UT Total Projected Population figures from official Hindi prelims PDF."
        )
        return result

    # 2020 PDF-only tables (TABLE-3A.3.pdf, TABLE-3A.4.pdf) & 2-2023.pdf TOC
    result = ParseResult(table_code=file_path.name, reporting_year=edition_year)
    if ingestion_role in {"pdf_rape_victim_age_groups", "pdf_rape_offender_relation"}:
        # Parse TOTAL ALL INDIA summary row reliably from text when present
        for line in full_text.splitlines():
            clean = re.sub(r"\s+", " ", line.replace("\xa0", " ")).strip()
            if clean.startswith("TOTAL ALL INDIA"):
                nums = re.findall(r"\d+(?:\.\d+)?", clean)
                if ingestion_role == "pdf_rape_victim_age_groups" and len(nums) >= 12:
                    # [3]..[14]: Cases Reported (0), Child groups (1..4), Child Total (5), Adult groups (6..9), Adult Total (10), Total Victims (11)
                    mapping = [
                        (0, "Cases Reported", "cases_registered", "cases"),
                        (5, "Child Victims Subtotal (Below 18 Years)", "victims", "female_victims"),
                        (10, "Adult Victims Subtotal (18+ Years)", "victims", "female_victims"),
                        (11, "Total Rape Victims (All Ages)", "victims", "female_victims"),
                    ]
                    for idx, sub_cat, mtype, unit in mapping:
                        val, _, raw_s = parse_numeric_value(nums[idx])
                        result.crime_rows.append(
                            ParsedCrimeObservation(
                                reporting_year=edition_year,
                                raw_geo_name="TOTAL ALL INDIA",
                                crime_domain="rape_age_groups",
                                crime_head="Rape (Sec. 376 IPC)",
                                sub_category=sub_cat,
                                metric_type=mtype,
                                unit=unit,
                                raw_value=raw_s,
                                normalized_value=val,
                                denominator_scope="none",
                                source_table=f"{file_path.name} ({edition_year} PDF)",
                                source_page_or_row="Page 1 / TOTAL ALL INDIA",
                            )
                        )
                elif ingestion_role == "pdf_rape_offender_relation" and len(nums) >= 7:
                    mapping = [
                        (0, "Offender Known to Victim (Total)", "cases_registered", "cases", "none"),
                        (1, "Family Members", "cases_registered", "cases", "none"),
                        (2, "Friends / Online-Friends / Live-in Partners / Separated Husband", "cases_registered", "cases", "none"),
                        (3, "Family Friends / Neighbours / Employer / Other Known Persons", "cases_registered", "cases", "none"),
                        (4, "Offenders Unknown or Not Identified", "cases_registered", "cases", "none"),
                        (5, "Total Rape Cases (Known + Unknown)", "cases_registered", "cases", "none"),
                        (6, "Share of Known Offender Cases (%)", "share_pct", "percent", "all_rape_cases"),
                    ]
                    for idx, sub_cat, mtype, unit, denom in mapping:
                        val, _, raw_s = parse_numeric_value(nums[idx])
                        result.crime_rows.append(
                            ParsedCrimeObservation(
                                reporting_year=edition_year,
                                raw_geo_name="TOTAL ALL INDIA",
                                crime_domain="rape_offender_relation",
                                crime_head="Rape (Sec. 376 IPC)",
                                sub_category=sub_cat,
                                metric_type=mtype,
                                unit=unit,
                                raw_value=raw_s,
                                normalized_value=val,
                                denominator_scope=denom,
                                source_table=f"{file_path.name} ({edition_year} PDF)",
                                source_page_or_row="Page 1 / TOTAL ALL INDIA",
                            )
                        )
        result.status = "partial"
        result.warnings.append(
            f"{file_path.name} was released by NCRB as PDF-only without a companion .xlsx file. "
            "National TOTAL ALL INDIA totals were extracted; State/UT rows require manual Excel verification."
        )
        return result

    result.status = "completed"
    result.extraction_notes.append(f"Inspected archival PDF {file_path.name} ({len(reader.pages)} pages).")
    return result


def parse_csv_dataset(
    file_path: Path,
    default_year: int,
    table_code: str = "MANUAL_CSV",
) -> ParseResult:
    """Reusable Pandas CSV parser supporting manual or normalized official CSV tables."""
    df = pd.read_csv(file_path)
    result = ParseResult(table_code=table_code, reporting_year=default_year)
    col_map = {c.strip().lower(): c for c in df.columns}

    geo_col = next((col_map[k] for k in ("state/ut", "state_ut", "state_name", "geographic_unit") if k in col_map), None)
    if not geo_col:
        result.status = "failed"
        result.warnings.append("CSV missing required geographic column (State/UT or state_name).")
        return result

    year_col = next((col_map[k] for k in ("year", "reporting_year") if k in col_map), None)
    head_col = next((col_map[k] for k in ("crime_head",) if k in col_map), None)
    domain_col = next((col_map[k] for k in ("crime_domain",) if k in col_map), None)
    metric_col = next((col_map[k] for k in ("metric_type",) if k in col_map), None)
    val_col = next((col_map[k] for k in ("value", "normalized_value", "cases", "count") if k in col_map), None)
    unit_col = next((col_map[k] for k in ("unit",) if k in col_map), None)

    if not val_col:
        result.status = "failed"
        result.warnings.append("CSV missing numeric value column (value / normalized_value / cases / count).")
        return result

    for idx, row in df.iterrows():
        raw_geo = str(row[geo_col]).strip()
        if _is_footer_or_section_marker(raw_geo):
            continue
        yr = int(row[year_col]) if year_col and pd.notna(row[year_col]) else default_year
        val, is_missing, raw_str = parse_numeric_value(None if pd.isna(row[val_col]) else row[val_col])
        result.crime_rows.append(
            ParsedCrimeObservation(
                reporting_year=yr,
                raw_geo_name=raw_geo,
                crime_domain=str(row[domain_col]).strip() if domain_col and pd.notna(row[domain_col]) else "rape_ipc_376",
                crime_head=str(row[head_col]).strip() if head_col and pd.notna(row[head_col]) else "Rape (Sec. 376 IPC)",
                sub_category="Total",
                metric_type=str(row[metric_col]).strip() if metric_col and pd.notna(row[metric_col]) else "cases_registered",
                unit=str(row[unit_col]).strip() if unit_col and pd.notna(row[unit_col]) else "cases",
                raw_value=raw_str if not is_missing else "",
                normalized_value=val,
                denominator_scope="none",
                source_table=table_code,
                source_page_or_row=f"CSV Row {idx + 2}",
            )
        )
    result.extraction_notes.append(f"Parsed {len(result.crime_rows)} rows from CSV {file_path.name}.")
    return result

