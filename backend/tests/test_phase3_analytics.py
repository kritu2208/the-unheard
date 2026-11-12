from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_year_filter_and_kpi_calculations():
    # 2022 full Sec. 376 + CAW
    res_2022 = client.get("/api/dashboard/overview?year=2022&metric=count")
    assert res_2022.status_code == 200
    d22 = res_2022.json()
    assert d22["selected_year"] == 2022
    kpis_22 = {k["id"]: k for k in d22["kpis"]}
    assert kpis_22["reported_cases"]["value"] == "31,516"
    assert kpis_22["reported_cases"]["available"] is True
    assert kpis_22["female_victims_and_rate"]["value"] == "31,982 · 4.7"
    assert kpis_22["caw_context"]["value"] == "445,256"
    assert kpis_22["national_disposal"]["value"] == "77.9% / 27.4%"

    # 2023 CAW Snapshot only (Sec. 376 must be explicitly Unavailable, never fabricated)
    res_2023 = client.get("/api/dashboard/overview?year=2023&metric=count")
    assert res_2023.status_code == 200
    d23 = res_2023.json()
    assert d23["selected_year"] == 2023
    kpis_23 = {k["id"]: k for k in d23["kpis"]}
    assert kpis_23["reported_cases"]["available"] is False
    assert kpis_23["reported_cases"]["value"] == "Unavailable"
    assert kpis_23["caw_context"]["value"] == "448,211"
    assert kpis_23["national_disposal"]["available"] is False


def test_metric_filter_and_disposal_unavailability_at_state_level():
    # Rate per 100k female population in 2022
    res_rate = client.get("/api/dashboard/geographic?year=2022&metric=rate_per_100k")
    assert res_rate.status_code == 200
    geo_rate = res_rate.json()
    assert geo_rate["metric_available"] is True
    assert len(geo_rate["states"]) == 36
    # Ranked #1 by rate_per_100k should have highest rate
    ranked = [s for s in geo_rate["states"] if s["rank_by_selected"] is not None]
    assert ranked[0]["rank_by_selected"] == 1
    assert ranked[0]["rate_per_100k_female"] >= ranked[1]["rate_per_100k_female"]

    # State-level Sec. 376 chargesheet/conviction must be explicitly unavailable
    res_cs = client.get("/api/dashboard/geographic?year=2022&metric=charge_sheet_pct")
    assert res_cs.status_code == 200
    geo_cs = res_cs.json()
    assert geo_cs["metric_available"] is False
    assert "3A.5" in (geo_cs["metric_unavailable_reason"] or "")
    assert all(s["charge_sheet_pct"] is None for s in geo_cs["states"])


def test_cross_component_state_and_trend_consistency():
    ov = client.get("/api/dashboard/overview?year=2021&metric=count").json()
    geo = client.get("/api/dashboard/geographic?year=2021&metric=count").json()
    tr = client.get("/api/dashboard/trends?start_year=2018&end_year=2021").json()

    assert tr["disaggregation_year"] == 2021
    assert len(tr["offender_relationship"]) == 4
    assert len(tr["age_group_breakdown"]) == 5

    # National 2021 trend point matches overview KPI
    pt_2021 = next(p for p in ov["national_trend"] if p["year"] == 2021)
    kpis_21 = {k["id"]: k for k in ov["kpis"]}
    assert kpis_21["reported_cases"]["value"] == f"{pt_2021['reported_cases']:,}"

    # State record values must never equal All-India national total
    rj = next(s for s in geo["states"] if s["state_code"] == "RJ")
    assert rj["reported_cases"] != pt_2021["reported_cases"]
    assert rj["reported_cases"] < pt_2021["reported_cases"]


def test_deterministic_insights_against_db_results():
    # National 2022 insights
    res_nat = client.get("/api/dashboard/insights?year=2022&state_code=ALL&metric=count")
    assert res_nat.status_code == 200
    ins_nat = res_nat.json()
    assert ins_nat["calculation_mode"] == "deterministic_db"
    assert ins_nat["llm_provider_configured"] is False
    assert len(ins_nat["insights"]) >= 3
    for item in ins_nat["insights"]:
        assert item["reporting_year"] == 2022
        assert item["metric"] == "count"
        assert item["observed_data"]
        assert item["interpretation"]
        assert item["source_table"]

    # State comparison insight (RJ vs MH in 2022)
    res_cmp = client.get(
        "/api/dashboard/insights?year=2022&state_code=RJ&metric=rate_per_100k&compare_code=MH"
    )
    assert res_cmp.status_code == 200
    ins_cmp = res_cmp.json()
    assert ins_cmp["selected_state_code"] == "RJ"
    cmp_cards = [i for i in ins_cmp["insights"] if i["category"] == "State Comparison"]
    assert len(cmp_cards) == 1
    assert "Rajasthan" in cmp_cards[0]["observed_data"]
    assert "Maharashtra" in cmp_cards[0]["observed_data"]

    # Missing-data year (2023) must surface Coverage Gap insight
    res_23 = client.get("/api/dashboard/insights?year=2023&state_code=ALL&metric=count")
    assert res_23.status_code == 200
    ins_23 = res_23.json()
    gap_cards = [i for i in ins_23["insights"] if i["category"] == "Data Coverage Gap"]
    assert len(gap_cards) == 1


def test_csv_export_correctness_and_source_traceability():
    # Valid 2022 RJ export
    res_ok = client.post(
        "/api/research/preview",
        json={"metric": "count", "years": [2022], "state_codes": ["RJ"]},
    )
    assert res_ok.status_code == 200
    body = res_ok.json()
    assert len(body["rows"]) == 1
    csv_text = body["csv_preview"]
    assert "# THE UNHEARD" in csv_text
    assert "source_table" in csv_text
    assert "Rajasthan" in csv_text
    assert "5399" in csv_text

    # 2018 RJ export must preserve UNAVAILABLE for Sec. 376 rather than fabricating 0
    res_18 = client.post(
        "/api/research/preview",
        json={"metric": "count", "years": [2018], "state_codes": ["RJ"]},
    )
    assert res_18.status_code == 200
    csv_18 = res_18.json()["csv_preview"]
    assert "UNAVAILABLE" in csv_18

