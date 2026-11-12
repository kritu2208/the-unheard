from fastapi.testclient import TestClient

from app.analytics.stats import compute_disposal_percentage, compute_rate_per_100k_female, compute_yoy_series
from app.main import app


def test_statistical_helpers_preserve_none_and_formulas():
    assert compute_rate_per_100k_female(5399, 391.0) == 13.81
    assert compute_rate_per_100k_female(5399, 0) is None
    assert compute_disposal_percentage(5067, 18517) == 27.36
    assert compute_disposal_percentage(10, 0) is None

    series = compute_yoy_series(
        [
            {"year": 2020, "reported_cases": 28046, "victims_count": 28153, "caw_total_cases": 371503},
            {"year": 2021, "reported_cases": 31677, "victims_count": 31878, "caw_total_cases": 428278},
            {"year": 2023, "reported_cases": None, "victims_count": None, "caw_total_cases": 448211},
        ]
    )
    assert series[1]["yoy_change_pct"] == 12.95
    # Non-consecutive jump 2021->2023 must NOT fabricate a YoY delta or turn None into NaN
    assert series[2]["reported_cases"] is None
    assert series[2]["yoy_change_pct"] is None
    assert series[2]["caw_yoy_change_pct"] is None


def test_verified_official_api_endpoints_and_missing_data_honesty():
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        hdata = health.json()
        assert hdata["database_connected"] is True
        assert hdata["data_mode"] == "VERIFIED_OFFICIAL_PHASE_2"
        assert hdata["latest_granular_year"] == 2022
        assert hdata["latest_publication_year"] == 2023

        ov22 = client.get("/api/dashboard/overview?year=2022&metric=count")
        assert ov22.status_code == 200
        d22 = ov22.json()
        kpi_map = {k["id"]: k for k in d22["kpis"]}
        assert kpi_map["reported_cases"]["value"] == "31,516"
        assert kpi_map["reported_cases"]["available"] is True
        assert kpi_map["national_disposal"]["value"] == "77.9% / 27.4%"
        assert d22["top_states"][0]["state_name"] == "Rajasthan"
        assert d22["top_states"][0]["reported_cases"] == 5399

        # 2023 must honestly report Sec. 376 unavailable while surfacing verified CAW 448,211
        ov23 = client.get("/api/dashboard/overview?year=2023&metric=count")
        assert ov23.status_code == 200
        k23 = {k["id"]: k for k in ov23.json()["kpis"]}
        assert k23["reported_cases"]["available"] is False
        assert k23["reported_cases"]["value"] == "Unavailable"
        assert k23["caw_context"]["value"] == "448,211"
        assert k23["caw_context"]["available"] is True

        # State-level Sec. 376 conviction rate must remain unavailable (never conflate with CAW Table 3A.8)
        geo_conv = client.get("/api/dashboard/geographic?year=2022&metric=conviction_pct")
        assert geo_conv.status_code == 200
        assert geo_conv.json()["metric_available"] is False
        assert "3A.8" in geo_conv.json()["metric_unavailable_reason"]

        trends = client.get("/api/dashboard/trends")
        assert trends.status_code == 200
        tdata = trends.json()
        assert len(tdata["offender_relationship"]) > 0
        assert len(tdata["age_group_breakdown"]) > 0

        datasets = client.get("/api/datasets")
        assert datasets.status_code == 200
        assert datasets.json()["total_datasets"] >= 30

        dq = client.get("/api/data-quality")
        assert dq.status_code == 200
        assert "INCONSISTENT_NATIONAL_TOTAL" not in {i["issue_code"] for i in dq.json()["issues"]}

        sources = client.get("/api/sources")
        assert sources.status_code == 200
        assert len(sources.json()["datasets"]) >= 4

        preview = client.post(
            "/api/research/preview",
            json={"metric": "count", "years": [2021, 2022], "state_codes": ["RJ", "MP"]},
        )
        assert preview.status_code == 200
        assert len(preview.json()["rows"]) == 4
        assert "Rajasthan" in preview.json()["csv_preview"]

