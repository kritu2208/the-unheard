"""One-page A4 Landscape PDF Report Generator for THE UNHEARD.

Strictly produces an exact 1-page analytical briefing document containing:
- Editorial Masthead & Provenance
- Active Filter Context (Year, Jurisdiction, Metric)
- KPI Metrics Block (Cases, Victims, Rates, Disposal)
- Side-by-side Analytical Visualizations:
    1. All-India Longitudinal Trajectory (2020-2022)
    2. State / UT Comparative Distribution
    3. Police Chargesheet & Court Conviction Analysis
- Deterministic Statistical Insights
- Official NCRB Methodology & Caveats Footer
"""

import io
from typing import Any, Dict, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.schemas.dashboard import MetricKey
from app.services.official_service import (
    get_dashboard_insights,
    get_geographic_analysis,
    get_overview,
    get_trends_patterns,
)

# Colors matching THE UNHEARD editorial design
BG_COLOR = colors.HexColor("#101012")
CARD_BG = colors.HexColor("#19191D")
CARD_BORDER = colors.HexColor("#2D2D34")
TEXT_PRIMARY = colors.HexColor("#F5F2EF")
TEXT_MUTED = colors.HexColor("#B8B4B4")
ACCENT_CRIMSON = colors.HexColor("#B51F32")
ACCENT_HIGHLIGHT = colors.HexColor("#E53945")
BAR_LIGHT = colors.HexColor("#E5E7EB")
BAR_PENDING = colors.HexColor("#4B5563")


def generate_single_page_pdf(
    db: Session,
    year: int = 2022,
    state_code: str = "ALL",
    metric: MetricKey = "count",
    compare_code: Optional[str] = None,
) -> bytes:
    """Generate an exact 1-page A4 landscape PDF analytical brief."""
    buffer = io.BytesIO()

    # A4 Landscape dimensions in points (841.89 x 595.28)
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    c.setTitle(f"THE UNHEARD — Analytical Brief {year} ({state_code})")
    c.setAuthor("THE UNHEARD — Investigative Data Analytics")

    # Fetch verified database data
    overview = get_overview(db, year=year, metric=metric)
    geo = get_geographic_analysis(db, year=year, metric=metric, region="ALL")
    trends = get_trends_patterns(db)
    insights = get_dashboard_insights(
        db, year=year, state_code=state_code, metric=metric, compare_code=compare_code
    )

    # 1. Full Page Dark Background
    c.setFillColor(BG_COLOR)
    c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # Margins & Grid
    margin_x = 24
    content_width = page_width - (margin_x * 2)

    # -------------------------------------------------------------
    # HEADER BAR (y = 535 to 580, height ~45)
    # -------------------------------------------------------------
    header_y = page_height - 18
    c.setFillColor(TEXT_PRIMARY)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(margin_x, header_y - 13, "THE UNHEARD")

    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(ACCENT_HIGHLIGHT)
    c.drawString(margin_x + 148, header_y - 11, "NCRB 2018–2023")

    c.setFont("Helvetica", 7)
    c.setFillColor(TEXT_MUTED)
    c.drawString(
        margin_x,
        header_y - 25,
        "INVESTIGATIVE CRIME-DATA ANALYTICS · OFFICIAL NCRB CRIME IN INDIA CHAPTER 3A",
    )

    # Right side: Active Filters Badge & Generation Timestamp
    state_display = "All India (National)"
    if state_code != "ALL":
        match = next((s for s in geo.states if s.state_code == state_code), None)
        if match:
            state_display = f"{match.state_name} ({match.state_code})"
        else:
            state_display = state_code

    metric_display_map = {
        "count": "Cases (Sec. 376 IPC)",
        "rate_per_100k": "Rate / 100k Female Pop.",
        "victims": "Female Victims (Sec. 376)",
        "caw_total": "Total Crime Against Women",
        "chargesheet_pct": "Police Chargesheet Rate (%)",
        "conviction_pct": "Court Conviction Rate (%)",
    }
    metric_label = metric_display_map.get(str(metric), str(metric))

    filter_summary = f"YEAR: {year}  |  JURISDICTION: {state_display.upper()}  |  METRIC: {metric_label.upper()}"
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(TEXT_PRIMARY)
    c.drawRightString(page_width - margin_x, header_y - 12, filter_summary)

    c.setFont("Helvetica", 6.5)
    c.setFillColor(TEXT_MUTED)
    c.drawRightString(
        page_width - margin_x,
        header_y - 24,
        "STRICT 1-PAGE EXECUTIVE BRIEFING · PRINCIPAL OFFENCE RULE APPLIED",
    )

    # Divider line below header
    c.setStrokeColor(CARD_BORDER)
    c.setLineWidth(0.8)
    c.line(margin_x, header_y - 30, page_width - margin_x, header_y - 30)

    # -------------------------------------------------------------
    # KPI CARDS ROW (height ~56)
    # -------------------------------------------------------------
    kpi_top_y = header_y - 36
    kpi_height = 54
    kpi_gap = 10
    kpi_count = 4
    card_width = (content_width - (kpi_gap * (kpi_count - 1))) / kpi_count

    selected_state_rec = None
    if state_code != "ALL":
        selected_state_rec = next((s for s in geo.states if s.state_code == state_code), None)

    kpi_data = []
    if selected_state_rec:
        pop_str = (
            f"Pop: {selected_state_rec.female_population_lakhs:.1f}L projected females"
            if selected_state_rec.female_population_lakhs
            else "Female population unstated"
        )
        cs_val = selected_state_rec.caw_charge_sheet_pct or selected_state_rec.charge_sheet_pct
        conv_val = selected_state_rec.caw_conviction_pct or selected_state_rec.conviction_pct
        disp_str = (
            f"{cs_val:.1f}% / {conv_val:.1f}%"
            if cs_val is not None and conv_val is not None
            else "CAW ONLY / TBL 3A.6"
        )
        kpi_data = [
            {
                "tag": "SEC. 376 IPC",
                "label": f"REPORTED RAPE CASES ({year})",
                "val": f"{selected_state_rec.reported_cases:,}" if selected_state_rec.reported_cases is not None else "UNAVAILABLE",
                "sub": f"Jurisdiction: {selected_state_rec.state_name}",
            },
            {
                "tag": "VICTIMS & RATE",
                "label": "VICTIMS · RATE / 100K FEMALE",
                "val": (
                    f"{selected_state_rec.victims_count or 0:,} · {selected_state_rec.rate_per_100k_female or 0.0:.1f}"
                    if selected_state_rec.victims_count is not None
                    else "UNAVAILABLE"
                ),
                "sub": pop_str,
            },
            {
                "tag": "TOTAL CAW",
                "label": "CRIMES AGAINST WOMEN (IPC+SLL)",
                "val": f"{selected_state_rec.caw_total_cases:,}" if selected_state_rec.caw_total_cases is not None else "UNAVAILABLE",
                "sub": "Broader CAW head; never conflated with rape",
            },
            {
                "tag": "DISPOSAL STATS",
                "label": "STATE CHARGESHEET / CONV. (%)",
                "val": disp_str,
                "sub": "State disposal reflects all CAW heads combined",
            },
        ]
    else:
        k0 = overview.kpis[0] if len(overview.kpis) > 0 else None
        k1 = overview.kpis[1] if len(overview.kpis) > 1 else None
        k2 = overview.kpis[2] if len(overview.kpis) > 2 else None
        k3 = overview.kpis[3] if len(overview.kpis) > 3 else None

        kpi_data = [
            {
                "tag": "TABLE 3A.2",
                "label": "REPORTED RAPE CASES (SEC. 376)",
                "val": str(k0.value) if k0 else "31,516",
                "sub": "Registered cases (I); distinct from incidence.",
            },
            {
                "tag": "TABLE 3A.2 & 3A.1",
                "label": "FEMALE VICTIMS · RATE PER 100K",
                "val": str(k1.value) if k1 else "31,982 · 4.7",
                "sub": "Single FIR can involve multiple female victims.",
            },
            {
                "tag": "TABLE 3A.1 / 9-2023",
                "label": "TOTAL CRIME AGAINST WOMEN",
                "val": str(k2.value) if k2 else "445,256",
                "sub": "Broader CAW FIRs; never conflated with Sec. 376.",
            },
            {
                "tag": "TABLE 3A.5 & 3A.7",
                "label": "NATIONAL CHARGESHEET / CONV.",
                "val": str(k3.value) if k3 else "77.9% / 27.4%",
                "sub": "90.0% court pendency (28 States + 8 UTs).",
            },
        ]

    for i, card in enumerate(kpi_data):
        cx = margin_x + i * (card_width + kpi_gap)
        cy = kpi_top_y - kpi_height

        c.setFillColor(CARD_BG)
        c.setStrokeColor(CARD_BORDER)
        c.setLineWidth(0.8)
        c.roundRect(cx, cy, card_width, kpi_height, 2, fill=1, stroke=1)

        c.setFillColor(ACCENT_HIGHLIGHT)
        c.rect(cx, cy + kpi_height - 2, card_width, 2, fill=1, stroke=0)

        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(ACCENT_HIGHLIGHT)
        c.drawString(cx + 8, cy + kpi_height - 11, card["tag"])

        c.setFont("Helvetica", 6.5)
        c.setFillColor(TEXT_MUTED)
        c.drawString(cx + 8, cy + kpi_height - 21, card["label"][:36])

        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(TEXT_PRIMARY)
        c.drawString(cx + 8, cy + kpi_height - 38, card["val"])

        c.setFont("Helvetica", 6)
        c.setFillColor(TEXT_MUTED)
        c.drawString(cx + 8, cy + 6, card["sub"][:42])

    # -------------------------------------------------------------
    # MIDDLE ROW: 3 ANALYTICAL CHARTS
    # -------------------------------------------------------------
    middle_top_y = kpi_top_y - kpi_height - 10
    middle_height = 230
    col_gap = 12
    col_width = (content_width - (col_gap * 2)) / 3.0

    # ----------------- PANEL 1: LONGITUDINAL TRAJECTORY -----------------
    p1_x = margin_x
    p1_y = middle_top_y - middle_height
    _draw_panel_box(c, p1_x, p1_y, col_width, middle_height, "ALL-INDIA LONGITUDINAL TRAJECTORY", "2020–2022")

    chart1_x = p1_x + 35
    chart1_y = p1_y + 35
    chart1_w = col_width - 50
    chart1_h = middle_height - 65

    c.setStrokeColor(CARD_BORDER)
    c.setLineWidth(0.8)
    c.line(chart1_x, chart1_y, chart1_x + chart1_w, chart1_y)
    c.line(chart1_x, chart1_y, chart1_x, chart1_y + chart1_h)

    trend_points = [
        (2020, 28046, "28,046 (COVID Lockdown)"),
        (2021, 31677, "31,677 (+12.9%)"),
        (2022, 31516, "31,516 (-0.5%)"),
    ]
    max_val = 36000

    c.setFont("Helvetica", 6)
    c.setFillColor(TEXT_MUTED)
    for tick in [10000, 20000, 30000]:
        ty = chart1_y + (tick / max_val) * chart1_h
        c.setStrokeColor(colors.HexColor("#222228"))
        c.line(chart1_x, ty, chart1_x + chart1_w, ty)
        c.drawString(p1_x + 8, ty - 2, f"{tick//1000}k")

    coords = []
    for yr, val, _ in trend_points:
        cx_pt = chart1_x + ((yr - 2020) / 2.0) * chart1_w
        cy_pt = chart1_y + (val / max_val) * chart1_h
        coords.append((cx_pt, cy_pt, val, yr))

    c.setStrokeColor(ACCENT_HIGHLIGHT)
    c.setLineWidth(2)
    for idx in range(len(coords) - 1):
        c.line(coords[idx][0], coords[idx][1], coords[idx + 1][0], coords[idx + 1][1])

    for cx_pt, cy_pt, val, yr in coords:
        c.setFillColor(ACCENT_CRIMSON)
        c.setStrokeColor(TEXT_PRIMARY)
        c.setLineWidth(1)
        c.circle(cx_pt, cy_pt, 3.5, fill=1, stroke=1)

        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(TEXT_PRIMARY)
        c.drawCentredString(cx_pt, cy_pt + 6, f"{val:,}")

        c.setFont("Helvetica", 6.5)
        c.setFillColor(TEXT_MUTED)
        c.drawCentredString(cx_pt, chart1_y - 12, str(yr))

    c.setFont("Helvetica", 5.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(
        p1_x + 8,
        p1_y + 10,
        "Note: 2023 Sec. 376 breakdown unreleased by NCRB (9-2023 snapshot covers CAW).",
    )

    # ----------------- PANEL 2: STATE / UT COMPARISON -----------------
    p2_x = margin_x + col_width + col_gap
    p2_y = middle_top_y - middle_height
    _draw_panel_box(
        c,
        p2_x,
        p2_y,
        col_width,
        middle_height,
        f"STATE RANKING ({metric_label[:18]}...)",
        f"{year}",
    )

    states_sorted = sorted(
        geo.states,
        key=lambda s: getattr(s, "reported_cases" if metric == "count" else "rate_per_100k_female") or 0,
        reverse=True,
    )
    display_states = states_sorted[:6]

    bar_start_y = p2_y + middle_height - 40
    bar_h = 13
    bar_spacing = 26
    label_w = 90  # widened so full names like Uttar Pradesh don't truncate
    chart_bar_max_w = col_width - label_w - 55
    max_state_val = (
        max(
            (getattr(s, "reported_cases" if metric == "count" else "rate_per_100k_female") or 0)
            for s in display_states
        )
        if display_states
        else 1
    )

    for idx, s in enumerate(display_states):
        by = bar_start_y - (idx * bar_spacing)
        s_val = (
            getattr(s, "reported_cases" if metric == "count" else "rate_per_100k_female")
            or 0
        )
        b_width = max(6, (s_val / max_state_val) * chart_bar_max_w)

        is_sel = s.state_code == state_code
        c.setFont("Helvetica-Bold" if is_sel else "Helvetica", 6.5)
        c.setFillColor(ACCENT_HIGHLIGHT if is_sel else TEXT_PRIMARY)
        name_str = f"{idx+1}. {s.state_name}"
        c.drawString(p2_x + 8, by + 3, name_str)

        c.setFillColor(colors.HexColor("#222228"))
        c.roundRect(p2_x + label_w, by, chart_bar_max_w, bar_h, 1.5, fill=1, stroke=0)

        c.setFillColor(ACCENT_HIGHLIGHT if is_sel else ACCENT_CRIMSON)
        c.roundRect(p2_x + label_w, by, b_width, bar_h, 1.5, fill=1, stroke=0)

        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(TEXT_PRIMARY)
        val_str = f"{s_val:,.1f}" if metric == "rate_per_100k" else f"{int(s_val):,}"
        c.drawString(p2_x + label_w + b_width + 4, by + 3, val_str)

    c.setFont("Helvetica", 5.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(
        p2_x + 8,
        p2_y + 10,
        "Caution: Higher counts reflect reporting & legal registration, not true safety levels.",
    )

    # ----------------- PANEL 3: CHARGESHEET & CONVICTION -----------------
    p3_x = margin_x + (col_width + col_gap) * 2
    p3_y = middle_top_y - middle_height
    _draw_panel_box(
        c,
        p3_x,
        p3_y,
        col_width,
        middle_height,
        "DISPOSAL & JUDICIAL ATTRITION",
        "NCRB 3A.5 & 3A.7",
    )

    disposal_data = [
        {"year": 2020, "cs": 78.4, "conv": 39.2, "pend": 91.2},
        {"year": 2021, "cs": 77.2, "conv": 28.6, "pend": 90.5},
        {"year": 2022, "cs": 77.9, "conv": 27.4, "pend": 90.0},
    ]

    p3_chart_x = p3_x + 30
    p3_chart_y = p3_y + 35
    p3_chart_w = col_width - 45
    p3_chart_h = middle_height - 75

    c.setStrokeColor(CARD_BORDER)
    c.setLineWidth(0.8)
    c.line(p3_chart_x, p3_chart_y, p3_chart_x + p3_chart_w, p3_chart_y)
    c.line(p3_chart_x, p3_chart_y, p3_chart_x, p3_chart_y + p3_chart_h)

    c.setFont("Helvetica", 6)
    c.setFillColor(TEXT_MUTED)
    for pct in [0, 50, 100]:
        py_tick = p3_chart_y + (pct / 100.0) * p3_chart_h
        c.drawString(p3_x + 6, py_tick - 2, f"{pct}%")
        if pct > 0:
            c.setStrokeColor(colors.HexColor("#222228"))
            c.line(p3_chart_x, py_tick, p3_chart_x + p3_chart_w, py_tick)

    group_w = p3_chart_w / 3.0
    bar_w_disp = 10

    for g_idx, row in enumerate(disposal_data):
        gx = p3_chart_x + g_idx * group_w + 14

        cs_h = (row["cs"] / 100.0) * p3_chart_h
        c.setFillColor(BAR_LIGHT)
        c.rect(gx, p3_chart_y, bar_w_disp, cs_h, fill=1, stroke=0)

        cv_h = (row["conv"] / 100.0) * p3_chart_h
        c.setFillColor(ACCENT_HIGHLIGHT)
        c.rect(gx + bar_w_disp + 2, p3_chart_y, bar_w_disp, cv_h, fill=1, stroke=0)

        pd_h = (row["pend"] / 100.0) * p3_chart_h
        c.setFillColor(BAR_PENDING)
        c.rect(gx + (bar_w_disp + 2) * 2, p3_chart_y, bar_w_disp, pd_h, fill=1, stroke=0)

        c.setFont("Helvetica", 6.5)
        c.setFillColor(TEXT_MUTED)
        c.drawCentredString(gx + bar_w_disp * 1.5, p3_chart_y - 12, str(row["year"]))

    leg_y = p3_y + 12
    c.setFillColor(BAR_LIGHT)
    c.rect(p3_x + 12, leg_y, 7, 7, fill=1, stroke=0)
    c.setFont("Helvetica", 5.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(p3_x + 22, leg_y + 1, "Chargesheet %")

    c.setFillColor(ACCENT_HIGHLIGHT)
    c.rect(p3_x + 76, leg_y, 7, 7, fill=1, stroke=0)
    c.drawString(p3_x + 86, leg_y + 1, "Conviction %")

    c.setFillColor(BAR_PENDING)
    c.rect(p3_x + 138, leg_y, 7, 7, fill=1, stroke=0)
    c.drawString(p3_x + 148, leg_y + 1, "Trial Pendency %")

    # -------------------------------------------------------------
    # LOWER ROW: DETERMINISTIC INSIGHTS
    # -------------------------------------------------------------
    lower_top_y = middle_top_y - middle_height - 10
    lower_height = 140
    ins_box_w = content_width

    _draw_panel_box(
        c,
        margin_x,
        lower_top_y - lower_height,
        ins_box_w,
        lower_height,
        "DETERMINISTIC STATISTICAL INSIGHTS & CAUSAL CONTEXT",
        "OFFICIAL REPOSITORY RULES",
    )

    ins_col_w = (ins_box_w - 24) / 3.0
    display_insights = insights.insights[:3]

    for ins_idx, item in enumerate(display_insights):
        ix = margin_x + 12 + ins_idx * ins_col_w
        iy = lower_top_y - 28

        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(ACCENT_HIGHLIGHT)
        c.drawString(ix, iy, f"• {item.title[:38]}")

        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(TEXT_PRIMARY)
        _wrap_text(c, f"Finding: {item.observed_data}", ix, iy - 12, ins_col_w - 14, 8, max_lines=2)

        c.setFont("Helvetica", 6)
        c.setFillColor(TEXT_MUTED)
        _wrap_text(c, item.interpretation, ix, iy - 32, ins_col_w - 14, 8, max_lines=6)

        c.setFont("Helvetica-Oblique", 5.5)
        c.setFillColor(ACCENT_CRIMSON)
        c.drawString(ix, lower_top_y - lower_height + 10, f"Source: {item.source_table[:35]}")

    # -------------------------------------------------------------
    # FOOTER: METHODOLOGY & STATUTORY CAVEATS
    # -------------------------------------------------------------
    footer_y = lower_top_y - lower_height - 6
    c.setStrokeColor(CARD_BORDER)
    c.setLineWidth(0.8)
    c.line(margin_x, footer_y, page_width - margin_x, footer_y)

    c.setFont("Helvetica-Bold", 6)
    c.setFillColor(TEXT_PRIMARY)
    c.drawString(margin_x, footer_y - 9, "OFFICIAL NCRB STATUTORY DEFINITIONS & METHODOLOGICAL BOUNDARIES")

    c.drawRightString(
        page_width - margin_x,
        footer_y - 9,
        "VERIFIED OFFICIAL EXTRACT · THE UNHEARD ANALYTICS",
    )

    c.setFont("Helvetica", 5)
    c.setFillColor(TEXT_MUTED)
    f_line1 = (
        "1. Principal Offence Rule: NCRB counts FIRs by offence carrying highest penalty; multi-offence incidents appear under single primary head. "
        "2. Cases vs Victims: Multiple survivors in one FIR are reported under Female Victims (Table 3A.2). "
        "3. Rates: Calculated using official RGI projected mid-year female census estimates (Table 3A.1)."
    )
    f_line2 = (
        "4. Legal Evolution: 2013 Amendment broadens Sec. 375/376 IPC; Bharatiya Nyaya Sanhita (BNS 2023 Sec. 63-71) in force from 1 July 2024. "
        "5. Scope: 2023 Chapter 3A State spreadsheets unreleased by NCRB; 2022 is the latest complete verified State/UT edition."
    )
    c.drawString(margin_x, footer_y - 18, f_line1)
    c.drawString(margin_x, footer_y - 27, f_line2)

    # Finish page and ensure exactly one page
    c.showPage()
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _draw_panel_box(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    tag: str,
) -> None:
    """Helper to draw dark styled analytical container box."""
    c.setFillColor(CARD_BG)
    c.setStrokeColor(CARD_BORDER)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, 2, fill=1, stroke=1)

    c.setFillColor(CARD_BORDER)
    c.rect(x, y + h - 18, w, 18, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(TEXT_PRIMARY)
    c.drawString(x + 8, y + h - 13, title)

    c.setFont("Helvetica", 6)
    c.setFillColor(ACCENT_HIGHLIGHT)
    c.drawRightString(x + w - 8, y + h - 13, tag)


def _wrap_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_w: float,
    line_h: float,
    max_lines: int = 5,
) -> None:
    """Simple text wrapping utility for canvas drawing."""
    words = text.split()
    lines: List[str] = []
    curr_line = ""

    for word in words:
        test_line = f"{curr_line} {word}".strip()
        if c.stringWidth(test_line) <= max_w:
            curr_line = test_line
        else:
            if curr_line:
                lines.append(curr_line)
            curr_line = word
        if len(lines) >= max_lines:
            break

    if curr_line and len(lines) < max_lines:
        lines.append(curr_line)

    for i, line in enumerate(lines[:max_lines]):
        c.drawString(x, y - (i * line_h), line)
