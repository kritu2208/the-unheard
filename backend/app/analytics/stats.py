from typing import Dict, List, Optional

import numpy as np
import pandas as pd


def compute_yoy_series(rows: List[Dict]) -> List[Dict]:
    """Compute year-over-year percentage changes separately on Sec. 376 Rape and CAW totals."""
    if not rows:
        return []

    df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)

    # Rape Sec. 376 YoY (only when consecutive years both have verified values)
    rape_vals = df["reported_cases"].astype("float64")
    rape_yoy = rape_vals.pct_change() * 100.0
    year_diff = df["year"].diff()

    caw_vals = df["caw_total_cases"].astype("float64")
    caw_yoy = caw_vals.pct_change() * 100.0

    results: List[Dict] = []
    int_fields = ("reported_cases", "victims_count", "caw_total_cases")
    float_fields = (
        "rate_per_100k_female",
        "charge_sheet_pct",
        "conviction_pct",
        "trial_pendency_pct",
        "caw_rate_per_100k_female",
    )
    for idx, record in enumerate(df.to_dict(orient="records")):
        ry: Optional[float] = None
        cy: Optional[float] = None
        if idx > 0 and year_diff.iloc[idx] == 1:
            if pd.notna(rape_yoy.iloc[idx]) and pd.notna(rape_vals.iloc[idx - 1]) and rape_vals.iloc[idx - 1] > 0:
                ry = round(float(rape_yoy.iloc[idx]), 2)
            if pd.notna(caw_yoy.iloc[idx]) and pd.notna(caw_vals.iloc[idx - 1]) and caw_vals.iloc[idx - 1] > 0:
                cy = round(float(caw_yoy.iloc[idx]), 2)
        record["yoy_change_pct"] = ry
        record["caw_yoy_change_pct"] = cy
        for k in int_fields:
            v = record.get(k)
            record[k] = None if v is None or pd.isna(v) else int(round(float(v)))
        for k in float_fields:
            v = record.get(k)
            record[k] = None if v is None or pd.isna(v) else round(float(v), 2)
        if pd.isna(record.get("statutory_note")):
            record["statutory_note"] = None
        results.append(record)
    return results


def compute_rate_per_100k_female(
    cases: Optional[float],
    female_population_lakhs: Optional[float],
) -> Optional[float]:
    """Compute crime rate per 100,000 female population strictly when valid female denominator exists.

    Formula: Rate = Cases / Projected_Female_Population_in_Lakhs (since 1 Lakh = 100,000).
    """
    if cases is None or female_population_lakhs is None or female_population_lakhs <= 0:
        return None
    return round(float(cases) / float(female_population_lakhs), 2)


def compute_disposal_percentage(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Compute percentage using NCRB numerator/denominator with zero-guard."""
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return round((float(numerator) / float(denominator)) * 100.0, 2)


def detect_series_anomalies(rows: List[Dict]) -> List[Dict]:
    """Identify statistically noteworthy shifts across official longitudinal data without inventing claims."""
    enriched = compute_yoy_series(rows)
    observations: List[Dict] = []

    caw_valid = [r for r in enriched if r.get("caw_yoy_change_pct") is not None]
    if len(caw_valid) >= 3:
        deltas = np.array([r["caw_yoy_change_pct"] for r in caw_valid], dtype=float)
        mean_d = float(np.mean(deltas))
        std_d = float(np.std(deltas, ddof=0)) or 1.0
        for row in caw_valid:
            z = (row["caw_yoy_change_pct"] - mean_d) / std_d
            if abs(z) >= 1.1:
                direction = "increase" if row["caw_yoy_change_pct"] > 0 else "decline"
                observations.append(
                    {
                        "id": f"caw-shift-{row['year']}",
                        "title": f"{row['year']} National CAW Shift ({row['caw_yoy_change_pct']:+.1f}% YoY)",
                        "category": "Longitudinal Variance · Crime Against Women",
                        "summary": (
                            f"Official NCRB Total Crime Against Women shifted by {row['caw_yoy_change_pct']:+.1f}% "
                            f"to {int(row['caw_total_cases']):,} FIRs in {row['year']} (z={z:+.2f} across 2018-2023). "
                            f"{row.get('statutory_note') or 'May reflect pandemic mobility restrictions and post-2020 reporting resumption.'}"
                        ),
                        "source_table": row.get("source_table", "NCRB TABLE 3A.1"),
                    }
                )

    rape_valid = [r for r in enriched if r.get("reported_cases") is not None and r.get("yoy_change_pct") is not None]
    for row in rape_valid:
        if abs(row["yoy_change_pct"]) >= 5.0:
            observations.append(
                {
                    "id": f"rape-shift-{row['year']}",
                    "title": f"{row['year']} Sec. 376 Rape Reporting Shift ({row['yoy_change_pct']:+.1f}% YoY)",
                    "category": "Official NCRB Delta · Sec. 376 IPC",
                    "summary": (
                        f"Police-registered Sec. 376 rape cases moved to {int(row['reported_cases']):,} "
                        f"({int(row['victims_count']):,} female victims) in {row['year']}, representing a "
                        f"{row['yoy_change_pct']:+.1f}% change from {row['year'] - 1}."
                    ),
                    "source_table": row.get("source_table", "NCRB TABLE 3A.2"),
                }
            )

    return observations
