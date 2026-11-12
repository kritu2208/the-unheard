import hashlib
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.records import GeographicUnit


@dataclass(frozen=True)
class CanonicalGeoDef:
    code: str
    canonical_name: str
    unit_type: str  # national | state | union_territory | subtotal
    region_zone: str
    aliases: Tuple[str, ...]
    boundary_notes: str = ""
    active_from_year: Optional[int] = None
    active_to_year: Optional[int] = None


CANONICAL_GEOS: Tuple[CanonicalGeoDef, ...] = (
    CanonicalGeoDef(
        "IN",
        "All-India",
        "national",
        "All-India",
        ("TOTAL ALL INDIA", "ALL INDIA", "INDIA", "TOTAL (ALL INDIA)"),
        "National total across 28 States and 8 Union Territories.",
    ),
    CanonicalGeoDef(
        "STATES",
        "Total States",
        "subtotal",
        "All-India",
        ("TOTAL STATE(S)", "TOTAL STATES"),
        "NCRB aggregate across all Indian States.",
    ),
    CanonicalGeoDef(
        "UTS",
        "Total Union Territories",
        "subtotal",
        "All-India",
        ("TOTAL UT(S)", "TOTAL UTS"),
        "NCRB aggregate across all Indian Union Territories.",
    ),
    # 28 States
    CanonicalGeoDef("AP", "Andhra Pradesh", "state", "South", ("ANDHRA PRADESH", "आंध्र प्रदेश")),
    CanonicalGeoDef("AR", "Arunachal Pradesh", "state", "Northeast", ("ARUNACHAL PRADESH", "अरुणाचल प्रदेश")),
    CanonicalGeoDef("AS", "Assam", "state", "Northeast", ("ASSAM", "असम")),
    CanonicalGeoDef("BR", "Bihar", "state", "East", ("BIHAR", "बिहार", "डबहार")),
    CanonicalGeoDef("CG", "Chhattisgarh", "state", "Central", ("CHHATTISGARH", "छत्तीसगढ़", "छत्तीसगढ")),
    CanonicalGeoDef("GA", "Goa", "state", "West", ("GOA", "गोवा")),
    CanonicalGeoDef("GJ", "Gujarat", "state", "West", ("GUJARAT", "गुजरात")),
    CanonicalGeoDef("HR", "Haryana", "state", "North", ("HARYANA", "हरियाणा")),
    CanonicalGeoDef("HP", "Himachal Pradesh", "state", "North", ("HIMACHAL PRADESH", "हिमाचल प्रदेश")),
    CanonicalGeoDef("JH", "Jharkhand", "state", "East", ("JHARKHAND", "झारखंड", "झारखण्ड")),
    CanonicalGeoDef("KA", "Karnataka", "state", "South", ("KARNATAKA", "कर्नाटक")),
    CanonicalGeoDef("KL", "Kerala", "state", "South", ("KERALA", "केरल")),
    CanonicalGeoDef("MP", "Madhya Pradesh", "state", "Central", ("MADHYA PRADESH", "मध्य प्रदेश")),
    CanonicalGeoDef("MH", "Maharashtra", "state", "West", ("MAHARASHTRA", "महाराष्ट्र")),
    CanonicalGeoDef("MN", "Manipur", "state", "Northeast", ("MANIPUR", "मणिपुर")),
    CanonicalGeoDef("ML", "Meghalaya", "state", "Northeast", ("MEGHALAYA", "मेघालय")),
    CanonicalGeoDef("MZ", "Mizoram", "state", "Northeast", ("MIZORAM", "मिजोरम")),
    CanonicalGeoDef("NL", "Nagaland", "state", "Northeast", ("NAGALAND", "नागालैंड")),
    CanonicalGeoDef("OD", "Odisha", "state", "East", ("ODISHA", "ORISSA", "ओडिशा")),
    CanonicalGeoDef("PB", "Punjab", "state", "North", ("PUNJAB", "पंजाब")),
    CanonicalGeoDef("RJ", "Rajasthan", "state", "North", ("RAJASTHAN", "राजस्थान")),
    CanonicalGeoDef("SK", "Sikkim", "state", "Northeast", ("SIKKIM", "सिक्किम", "डसक्किम")),
    CanonicalGeoDef("TN", "Tamil Nadu", "state", "South", ("TAMIL NADU", "TAMILNADU", "तमिलनाडु", "तडमलनािु")),
    CanonicalGeoDef("TS", "Telangana", "state", "South", ("TELANGANA", "तेलंगाना")),
    CanonicalGeoDef("TR", "Tripura", "state", "Northeast", ("TRIPURA", "त्रिपुरा")),
    CanonicalGeoDef("UP", "Uttar Pradesh", "state", "North", ("UTTAR PRADESH", "उत्तर प्रदेश")),
    CanonicalGeoDef("UK", "Uttarakhand", "state", "North", ("UTTARAKHAND", "UTTARANCHAL", "उत्तराखंड")),
    CanonicalGeoDef("WB", "West Bengal", "state", "East", ("WEST BENGAL", "पश्चिम बंगाल")),
    # 8 Union Territories (+ pre-2020 constituents if separately listed)
    CanonicalGeoDef(
        "AN",
        "Andaman & Nicobar Islands",
        "union_territory",
        "Islands",
        ("A & N ISLANDS", "A&N ISLANDS", "ANDAMAN & NICOBAR ISLANDS", "ANDAMAN AND NICOBAR ISLANDS"),
    ),
    CanonicalGeoDef("CH", "Chandigarh", "union_territory", "North", ("CHANDIGARH", "चंडीगढ़")),
    CanonicalGeoDef(
        "DN",
        "Dadra & Nagar Haveli and Daman & Diu",
        "union_territory",
        "West",
        (
            "D & N HAVELI AND DAMAN & DIU",
            "D&N HAVELI AND DAMAN & DIU",
            "DADRA & NAGAR HAVELI AND DAMAN & DIU",
            "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
            "D&N HAVELI+",
            "D & N HAVELI+",
            "D&N HAVELI",
        ),
        boundary_notes=(
            "Dadra & Nagar Haveli and Daman & Diu merged into one Union Territory on 26 Jan 2020. "
            "NCRB 2020 edition marks combined 2018-2020 figures with '+'."
        ),
        active_from_year=2020,
    ),
    CanonicalGeoDef(
        "DD",
        "Daman & Diu (Pre-2020)",
        "union_territory",
        "West",
        ("DAMAN & DIU", "DAMAN & DIU+", "DAMAN AND DIU"),
        boundary_notes="Merged with Dadra & Nagar Haveli into a single Union Territory on 26 Jan 2020.",
        active_to_year=2019,
    ),
    CanonicalGeoDef(
        "DL",
        "Delhi (NCT)",
        "union_territory",
        "North",
        ("DELHI UT", "DELHI", "NCT OF DELHI", "DELHI (NCT)"),
    ),
    CanonicalGeoDef(
        "JK",
        "Jammu & Kashmir",
        "union_territory",
        "North",
        ("JAMMU & KASHMIR", "JAMMU AND KASHMIR", "JAMMU & KASHMIR*", "JAMMU & KASHMIR@"),
        boundary_notes=(
            "Reorganized from State to Union Territory on 31 Oct 2019 alongside UT of Ladakh. "
            "NCRB 2018-2019 pre-split figures include Ladakh ('*' footnote)."
        ),
    ),
    CanonicalGeoDef(
        "LA",
        "Ladakh",
        "union_territory",
        "North",
        ("LADAKH", "LADAKH @", "LADAKH@"),
        boundary_notes="Created as a separate Union Territory on 31 Oct 2019; 2018 data included under erstwhile Jammu & Kashmir.",
        active_from_year=2019,
    ),
    CanonicalGeoDef("LD", "Lakshadweep", "union_territory", "Islands", ("LAKSHADWEEP",)),
    CanonicalGeoDef("PY", "Puducherry", "union_territory", "South", ("PUDUCHERRY", "PONDICHERRY")),
)


def _clean_geo_key(raw_name: str) -> str:
    text = str(raw_name or "").replace("\xa0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text.upper()


def _strip_footnote_markers(key: str) -> str:
    return re.sub(r"[\s\*@\+]+$", "", key).strip()


_ALIAS_MAP: Dict[str, CanonicalGeoDef] = {}
for _geo in CANONICAL_GEOS:
    _ALIAS_MAP[_clean_geo_key(_geo.canonical_name)] = _geo
    for _alias in _geo.aliases:
        _ALIAS_MAP[_clean_geo_key(_alias)] = _geo
        _ALIAS_MAP[_strip_footnote_markers(_clean_geo_key(_alias))] = _geo


def resolve_canonical_geo(raw_name: str) -> Optional[CanonicalGeoDef]:
    """Normalize any NCRB State/UT/All-India raw label into a canonical GeographicUnit definition."""
    key = _clean_geo_key(raw_name)
    if key in _ALIAS_MAP:
        return _ALIAS_MAP[key]
    stripped = _strip_footnote_markers(key)
    if stripped in _ALIAS_MAP:
        return _ALIAS_MAP[stripped]
    # Handle spacing around &
    normalized_amp = re.sub(r"\s*&\s*", " & ", stripped)
    if normalized_amp in _ALIAS_MAP:
        return _ALIAS_MAP[normalized_amp]
    return None


def ensure_geographic_units(db: Session) -> Dict[str, GeographicUnit]:
    """Ensure all canonical Indian geographic units exist in the DB and return a code->ORM lookup."""
    existing = {u.code: u for u in db.scalars(select(GeographicUnit)).all()}
    for geo in CANONICAL_GEOS:
        if geo.code not in existing:
            unit = GeographicUnit(
                code=geo.code,
                canonical_name=geo.canonical_name,
                unit_type=geo.unit_type,
                region_zone=geo.region_zone,
                aliases_json=json.dumps(list(geo.aliases)),
                boundary_notes=geo.boundary_notes,
                active_from_year=geo.active_from_year,
                active_to_year=geo.active_to_year,
            )
            db.add(unit)
            existing[geo.code] = unit
    db.flush()
    return existing


def parse_numeric_value(raw_val: object) -> Tuple[Optional[float], bool, str]:
    """Parse an NCRB cell safely without fabricating zeroes for genuinely missing strings."""
    if raw_val is None:
        return None, True, ""
    if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool):
        return float(raw_val), False, str(raw_val)

    text = str(raw_val).replace("\xa0", " ").strip()
    if text == "" or text.lower() in {"na", "n.a.", "nil*", "not available", "-", "—", "--"}:
        return None, True, text

    cleaned = text.replace(",", "").strip()
    # Strip trailing NCRB footnote markers ('*', '@', '+') while preserving original string in raw_val
    cleaned_no_marker = re.sub(r"[\*@\+]+$", "", cleaned).strip()
    try:
        return float(cleaned_no_marker), False, text
    except ValueError:
        return None, True, text


def compute_file_sha256(file_path: str) -> str:
    """Compute SHA-256 hex digest of an original file without modifying it."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_record_fingerprint(
    dataset_key: str,
    reporting_year: int,
    geo_code: str,
    crime_domain: str,
    crime_head: str,
    sub_category: str,
    metric_type: str,
) -> str:
    """Deterministic SHA-256 fingerprint preventing duplicate observations on reruns."""
    payload = "|".join(
        [
            dataset_key.strip(),
            str(reporting_year),
            geo_code.strip(),
            crime_domain.strip(),
            crime_head.strip(),
            sub_category.strip(),
            metric_type.strip(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def detect_boundary_footnote_notes(raw_name: str, reporting_year: int) -> List[str]:
    """Capture NCRB historical boundary footnote markers ('*', '@', '+') for transparency."""
    notes: List[str] = []
    if "*" in raw_name:
        notes.append(f"{reporting_year} figure reflects pre-2019 undivided Jammu & Kashmir boundary ('*' marker).")
    if "@" in raw_name:
        notes.append(f"{reporting_year} figure reflects reorganized UT boundary ('@' marker).")
    if "+" in raw_name:
        notes.append(f"{reporting_year} figure reflects combined D&N Haveli and Daman & Diu reporting ('+' marker).")
    return notes

