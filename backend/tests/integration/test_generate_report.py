"""Integration tests: full HTTP pipeline from upload through report generation.

These tests spin up the FastAPI app via TestClient (no real server needed) and
exercise the complete request/response cycle including the service layer and all
processing functions.

Uploads are retained for the configured TTL so generate/export calls can reuse
the processed workbook cache. The function-scoped fixture keeps each generate
test isolated from previous report state.
"""
import io

import openpyxl
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Helpers
def _upload(workbook_bytes: bytes) -> dict:
    resp = client.post(
        "/upload",
        files={"file": ("sample.xlsx", io.BytesIO(workbook_bytes), _XLSX_MIME)},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _metric(data: dict, key: str) -> dict:
    """Look up a metric section by key from a /reports/generate response."""
    return next(m for m in data["metrics"] if m["key"] == key)


def _metric_keys(data: dict) -> set:
    return {m["key"] for m in data["metrics"]}


# Conftest scenario indices (0-based, matching Info sheet order):
#   0 Base_IV | 1 Outage_IV | 2 Final_IV
#   3 Base_EV | 4 Outage_EV | 5 Final_EV
_IV_CHAIN_SIMPLE  = [0, 2]        # Base_IV → Final_IV  (1 step pair)
_EV_CHAIN_SIMPLE  = [3, 5]        # Base_EV → Final_EV  (1 step pair)
_IV_CHAIN_3STEP   = [0, 1, 2]     # 3-scenario chain   (2 steps + 1 cumulative = 3 pairs)
_EV_CHAIN_3STEP   = [3, 4, 5]


# Fixtures
@pytest.fixture(scope="module")
def uploaded_module(sample_workbook_bytes):
    """Module-scoped upload used by read-only endpoints (preview-chain, data-preview)."""
    return _upload(sample_workbook_bytes)


@pytest.fixture
def uploaded(sample_workbook_bytes):
    """Function-scoped upload so each generate test gets isolated state."""
    return _upload(sample_workbook_bytes)

# POST /upload
class TestUpload:
    def test_returns_200(self, sample_workbook_bytes):
        resp = client.post(
            "/upload",
            files={"file": ("sample.xlsx", io.BytesIO(sample_workbook_bytes), _XLSX_MIME)},
        )
        assert resp.status_code == 200

    def test_upload_id_is_present(self, uploaded_module):
        assert "upload_id" in uploaded_module

    def test_six_scenarios_returned(self, uploaded_module):
        assert len(uploaded_module["scenarios"]) == 6

    def test_scenario_names(self, uploaded_module):
        names = {s["scenario_name"] for s in uploaded_module["scenarios"]}
        assert names == {"Base_IV", "Outage_IV", "Final_IV", "Base_EV", "Outage_EV", "Final_EV"}

    def test_machine_list_returned(self, uploaded_module):
        assert uploaded_module["machines"] == ["MACHINE_A"]

    def test_available_metrics_returned(self, uploaded_module):
        keys = {m["key"] for m in uploaded_module["available_metrics"]}
        assert keys == {"ev", "iv", "pp", "iv_heat", "heat_prod"}

    def test_only_core_three_metrics_selected_by_default(self, uploaded_module):
        defaults = {m["key"]: m["default_selected"] for m in uploaded_module["available_metrics"]}
        assert defaults == {"ev": True, "iv": True, "pp": True, "iv_heat": False, "heat_prod": False}

    def test_rejects_non_xlsx(self):
        resp = client.post(
            "/upload",
            files={"file": ("bad.csv", io.BytesIO(b"a,b"), "text/csv")},
        )
        assert resp.status_code == 400

    def test_invalid_workbook_structure_returns_422(self):
        workbook = openpyxl.Workbook()
        workbook.active.title = "Info"
        buf = io.BytesIO()
        workbook.save(buf)
        buf.seek(0)

        resp = client.post(
            "/upload",
            files={"file": ("missing-data.xlsx", buf, _XLSX_MIME)},
        )

        assert resp.status_code == 422


# POST /reports/preview-chain
class TestPreviewChain:
    def test_returns_200(self, uploaded_module):
        resp = client.post("/reports/preview-chain", json={
            "upload_id": uploaded_module["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert resp.status_code == 200

    def test_one_pair_for_two_element_chain(self, uploaded_module):
        resp = client.post("/reports/preview-chain", json={
            "upload_id": uploaded_module["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        data = resp.json()
        assert len(data["iv_pairs"]) == 1
        assert len(data["ev_pairs"]) == 1

    def test_three_pairs_for_three_element_chain(self, uploaded_module):
        resp = client.post("/reports/preview-chain", json={
            "upload_id": uploaded_module["upload_id"],
            "iv_chain": _IV_CHAIN_3STEP,
            "ev_chain": _EV_CHAIN_3STEP,
        })
        data = resp.json()
        # 2 steps + 1 cumulative = 3
        assert len(data["iv_pairs"]) == 3

    def test_pair_names_match_scenarios(self, uploaded_module):
        resp = client.post("/reports/preview-chain", json={
            "upload_id": uploaded_module["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        pair = resp.json()["iv_pairs"][0]
        assert pair["left_name"] == "Base_IV"
        assert pair["right_name"] == "Final_IV"

    def test_unknown_upload_returns_404(self):
        resp = client.post("/reports/preview-chain", json={
            "upload_id": "00000000-0000-0000-0000-000000000000",
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert resp.status_code == 404


# POST /reports/data-preview
class TestDataPreview:
    def test_new_iv_heat_dashboards_are_returned(self, uploaded_module):
        resp = client.post("/reports/data-preview", json={
            "upload_id": uploaded_module["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["iv_heat_monthly"]) == 2
        assert len(data["iv_heat_deltas"]) == 1
        assert len(data["heat_prod_monthly"]) == 2
        assert len(data["heat_prod_deltas"]) == 1
        assert "heat_cost_monthly" not in data
        assert "heat_cost_deltas" not in data

    def test_new_dashboard_preview_values_use_iv_chain(self, uploaded_module):
        resp = client.post("/reports/data-preview", json={
            "upload_id": uploaded_module["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        data = resp.json()
        iv_heat_delta = data["iv_heat_deltas"][0]["rows"][0]["values"]
        heat_prod_delta = data["heat_prod_deltas"][0]["rows"][0]["values"]
        assert iv_heat_delta == [800.0, 800.0]
        assert heat_prod_delta == [8.0, 8.0]

# POST /reports/generate
class TestGenerateReport:
    def test_returns_200(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert resp.status_code == 200

    def test_report_id_and_upload_id_present(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        data = resp.json()
        assert "report_id" in data
        # upload_id echoed back so clients can recompute with a different machine filter
        assert data["upload_id"] == uploaded["upload_id"]

    def test_monthly_tables_count(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        data = resp.json()
        # base + final = 2 monthly tables per metric
        for key in ("ev", "iv", "pp", "iv_heat", "heat_prod"):
            assert len(_metric(data, key)["monthly"]) == 2
        assert "heat_cost" not in _metric_keys(data)

    def test_delta_tables_count_simple_chain(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        data = resp.json()
        # 2-element chain → 1 delta pair (step only, no cumulative)
        for key in ("ev", "iv", "pp", "iv_heat", "heat_prod"):
            assert len(_metric(data, key)["deltas"]) == 1
        assert "heat_cost" not in _metric_keys(data)

    def test_delta_tables_count_three_step_chain(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_3STEP,
            "ev_chain": _EV_CHAIN_3STEP,
        })
        data = resp.json()
        # 3-element chain → 2 steps + 1 cumulative = 3 delta pairs
        assert len(_metric(data, "ev")["deltas"]) == 3
        assert len(_metric(data, "iv_heat")["deltas"]) == 3
        assert len(_metric(data, "heat_prod")["deltas"]) == 3

    def test_new_iv_heat_metrics_use_iv_chain_values(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        data = resp.json()
        iv_heat_delta = _metric(data, "iv_heat")["deltas"][0]
        assert iv_heat_delta["left_total"] == pytest.approx(3600.0)
        assert iv_heat_delta["right_total"] == pytest.approx(6800.0)
        assert iv_heat_delta["delta_total"] == pytest.approx(3200.0)
        assert _metric(data, "heat_prod")["deltas"][0]["delta_total"] == pytest.approx(32.0)

    def test_ev_delta_yearly_values(self, uploaded):
        """Verify the yearly aggregate numbers match known fixture values.

        Base_EV=500, Final_EV=1300 per row.
        4 rows per year (2 tariffs × 2 months) → totals: 2000 / 5200 / delta 3200.
        """
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        delta = _metric(resp.json(), "ev")["deltas"][0]
        assert delta["left_total"] == pytest.approx(2000.0)
        assert delta["right_total"] == pytest.approx(5200.0)
        assert delta["delta_total"] == pytest.approx(3200.0)

    def test_delta_row_year_is_2026(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        rows = _metric(resp.json(), "ev")["deltas"][0]["rows"]
        assert len(rows) == 1
        assert rows[0]["year"] == 2026
        assert "machine_name" not in rows[0]

    def test_selected_metrics_filters_returned_tables(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
            "selected_metrics": ["ev", "iv"],
        })
        data = resp.json()
        assert _metric_keys(data) == {"ev", "iv"}
        assert len(_metric(data, "ev")["monthly"]) == 2
        assert len(_metric(data, "iv")["monthly"]) == 2

    def test_selected_metrics_unknown_key_is_ignored(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
            "selected_metrics": ["ev", "not_a_real_metric"],
        })
        data = resp.json()
        assert _metric_keys(data) == {"ev"}

    def test_no_selected_metrics_returns_all_available(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        data = resp.json()
        assert _metric_keys(data) == {"ev", "iv", "pp", "iv_heat", "heat_prod"}
        for key in ("ev", "iv", "pp", "iv_heat", "heat_prod"):
            assert len(_metric(data, key)["monthly"]) == 2

    def test_machine_filter_with_known_machine(self, uploaded):
        """Filtering by the only machine in the fixture yields the same totals.

        Since uploads are no longer deleted after generate, we can reuse the
        same upload_id for both the unfiltered and the filtered request.
        """
        resp_no_filter = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        totals_no_filter = _metric(resp_no_filter.json(), "ev")["deltas"][0]["delta_total"]

        resp_filtered = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
            "selected_machines": ["MACHINE_A"],
        })
        totals_filtered = _metric(resp_filtered.json(), "ev")["deltas"][0]["delta_total"]
        assert totals_filtered == pytest.approx(totals_no_filter)

    def test_recompute_with_same_upload_id(self, uploaded):
        """The upload file persists after generate, allowing machine-filter recomputes."""
        uid = uploaded["upload_id"]
        # First call — all machines
        r1 = client.post("/reports/generate", json={
            "upload_id": uid, "iv_chain": _IV_CHAIN_SIMPLE, "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert r1.status_code == 200
        # Second call — same upload_id, explicit machine filter; must not 404
        r2 = client.post("/reports/generate", json={
            "upload_id": uid, "iv_chain": _IV_CHAIN_SIMPLE, "ev_chain": _EV_CHAIN_SIMPLE,
            "selected_machines": ["MACHINE_A"],
        })
        assert r2.status_code == 200
        # Values must be equal (only one machine in fixture)
        assert _metric(r1.json(), "ev")["deltas"][0]["delta_total"] == pytest.approx(
            _metric(r2.json(), "ev")["deltas"][0]["delta_total"]
        )

    def test_unknown_upload_returns_404(self):
        resp = client.post("/reports/generate", json={
            "upload_id": "00000000-0000-0000-0000-000000000000",
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert resp.status_code == 404

    def test_invalid_chain_index_returns_422(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": [0, 99],   # index 99 does not exist
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert resp.status_code == 422


# POST /reports/export
class TestExportReport:
    def test_returns_200(self, uploaded):
        resp = client.post("/reports/export", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert resp.status_code == 200

    def test_content_type_is_xlsx(self, uploaded):
        resp = client.post("/reports/export", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert _XLSX_MIME in resp.headers["content-type"]

    def test_content_disposition_attachment(self, uploaded):
        resp = client.post("/reports/export", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_response_is_valid_xlsx(self, uploaded):
        """The bytes returned must be a loadable Excel workbook."""
        resp = client.post("/reports/export", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        import io as _io
        import openpyxl
        wb = openpyxl.load_workbook(_io.BytesIO(resp.content))
        assert "EV_month" in wb.sheetnames
        assert "IV_Heat_month" in wb.sheetnames
        assert "Heat_Prod_sheet" in wb.sheetnames
        assert "Heat_Cost_month" not in wb.sheetnames
        assert "Heat_Cost_sheet" not in wb.sheetnames
        assert "Info" in wb.sheetnames
        assert "Data" in wb.sheetnames

    def test_unknown_upload_returns_404(self):
        resp = client.post("/reports/export", json={
            "upload_id": "00000000-0000-0000-0000-000000000000",
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert resp.status_code == 404

    def test_invalid_chain_returns_422(self, uploaded):
        resp = client.post("/reports/export", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": [0, 99],
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        assert resp.status_code == 422

