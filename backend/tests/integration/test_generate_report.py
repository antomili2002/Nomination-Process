"""Integration tests: full HTTP pipeline from upload through report generation.

These tests spin up the FastAPI app via TestClient (no real server needed) and
exercise the complete request/response cycle including the service layer and all
processing functions.

Upload fixture is function-scoped for the generate tests because
POST /reports/generate schedules the uploaded file for deletion as a background
task.  A fresh upload is therefore required for each independent generate call.
"""
import io

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
    """Function-scoped upload — each generate test gets a fresh file."""
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

    def test_rejects_non_xlsx(self):
        resp = client.post(
            "/upload",
            files={"file": ("bad.csv", io.BytesIO(b"a,b"), "text/csv")},
        )
        assert resp.status_code == 400


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
        assert len(data["ev_monthly"]) == 2
        assert len(data["iv_monthly"]) == 2
        assert len(data["pp_monthly"]) == 2

    def test_delta_tables_count_simple_chain(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        data = resp.json()
        # 2-element chain → 1 delta pair (step only, no cumulative)
        assert len(data["ev_deltas"]) == 1
        assert len(data["iv_deltas"]) == 1
        assert len(data["pp_deltas"]) == 1

    def test_delta_tables_count_three_step_chain(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_3STEP,
            "ev_chain": _EV_CHAIN_3STEP,
        })
        data = resp.json()
        # 3-element chain → 2 steps + 1 cumulative = 3 delta pairs
        assert len(data["ev_deltas"]) == 3

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
        delta = resp.json()["ev_deltas"][0]
        assert delta["left_total"] == pytest.approx(2000.0)
        assert delta["right_total"] == pytest.approx(5200.0)
        assert delta["delta_total"] == pytest.approx(3200.0)

    def test_delta_row_year_is_2026(self, uploaded):
        resp = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
        })
        rows = resp.json()["ev_deltas"][0]["rows"]
        assert len(rows) == 1
        assert rows[0]["year"] == 2026

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
        totals_no_filter = resp_no_filter.json()["ev_deltas"][0]["delta_total"]

        resp_filtered = client.post("/reports/generate", json={
            "upload_id": uploaded["upload_id"],
            "iv_chain": _IV_CHAIN_SIMPLE,
            "ev_chain": _EV_CHAIN_SIMPLE,
            "selected_machines": ["MACHINE_A"],
        })
        totals_filtered = resp_filtered.json()["ev_deltas"][0]["delta_total"]
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
        assert r1.json()["ev_deltas"][0]["delta_total"] == pytest.approx(
            r2.json()["ev_deltas"][0]["delta_total"]
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

