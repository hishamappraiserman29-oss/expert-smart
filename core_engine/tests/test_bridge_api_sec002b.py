"""
SEC-002b tests — mass appraisal + valuation pipeline auth hardening.

All 21 endpoints now require @require_auth:

Mass appraisal (10):
  POST /api/mass-appraisal/preview
  POST /api/mass-appraisal/run
  POST /api/mass-appraisal/export-xlsx
  POST /api/mass-appraisal/sales/verify
  POST /api/mass-appraisal/sales/time-adjust
  POST /api/mass-appraisal/sales/adjust
  POST /api/mass-appraisal/ratio-study/run
  POST /api/mass-appraisal/calibration/preview
  POST /api/mass-appraisal/calibration/sandbox
  POST /api/mass-appraisal/import-xlsx

Valuation pipeline (11):
  POST /api/valuation/full
  POST /api/valuation/report
  POST /api/valuation/land
  POST /api/valuation/audit
  POST /api/valuation/portfolio
  POST /api/valuation/portfolio/performance
  POST /api/valuation/batch
  GET  /api/valuation/batch/<id>
  GET  /api/valuation/batch
  POST /api/valuation/avm
  POST /api/valuation/avm/batch
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parents[1]
_ROOT = _CORE.parent
for _p in (str(_CORE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.chdir(str(_CORE))

from bridge_api import app  # noqa: E402
from auth.tokens import generate_token  # noqa: E402

_USER        = "regular-sec002b-user"
_TEST_SECRET = "test-secret-for-sec002b"


def _auth() -> dict:
    return {"Authorization": f"Bearer {generate_token(_USER)}"}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", "admin-sec002b")
    monkeypatch.delenv("JWT_TTL_SECONDS", raising=False)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── helpers ───────────────────────────────────────────────────────────────────

def _assert_auth_gated(resp_no_token, resp_with_token):
    """No token → 401. Valid token → handler reached (not 401/403)."""
    assert resp_no_token.status_code == 401, (
        f"Expected 401 without token, got {resp_no_token.status_code}"
    )
    assert resp_with_token.status_code not in (401, 403), (
        f"Expected handler reached with token, got {resp_with_token.status_code}"
    )


# ── Mass appraisal ────────────────────────────────────────────────────────────

class TestMassAppraisalAuthGated:

    def test_preview_requires_auth(self, client):
        r_anon = client.post("/api/mass-appraisal/preview", json={})
        r_auth = client.post("/api/mass-appraisal/preview", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_run_requires_auth(self, client):
        r_anon = client.post("/api/mass-appraisal/run", json={})
        r_auth = client.post("/api/mass-appraisal/run", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_export_xlsx_requires_auth(self, client):
        r_anon = client.post("/api/mass-appraisal/export-xlsx", json={})
        r_auth = client.post("/api/mass-appraisal/export-xlsx", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_sales_verify_requires_auth(self, client):
        r_anon = client.post("/api/mass-appraisal/sales/verify", json={})
        r_auth = client.post("/api/mass-appraisal/sales/verify", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_sales_time_adjust_requires_auth(self, client):
        r_anon = client.post("/api/mass-appraisal/sales/time-adjust", json={})
        r_auth = client.post("/api/mass-appraisal/sales/time-adjust", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_sales_adjust_requires_auth(self, client):
        r_anon = client.post("/api/mass-appraisal/sales/adjust", json={})
        r_auth = client.post("/api/mass-appraisal/sales/adjust", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_ratio_study_requires_auth(self, client):
        r_anon = client.post("/api/mass-appraisal/ratio-study/run", json={})
        r_auth = client.post("/api/mass-appraisal/ratio-study/run", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_calibration_preview_requires_auth(self, client):
        r_anon = client.post("/api/mass-appraisal/calibration/preview", json={})
        r_auth = client.post("/api/mass-appraisal/calibration/preview", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_calibration_sandbox_requires_auth(self, client):
        r_anon = client.post("/api/mass-appraisal/calibration/sandbox", json={})
        r_auth = client.post("/api/mass-appraisal/calibration/sandbox", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_import_xlsx_requires_auth(self, client):
        import io
        r_anon = client.post("/api/mass-appraisal/import-xlsx",
                             data={"file": (io.BytesIO(b"fake"), "template.xlsx")},
                             content_type="multipart/form-data")
        r_auth = client.post("/api/mass-appraisal/import-xlsx",
                             data={"file": (io.BytesIO(b"fake"), "template.xlsx")},
                             content_type="multipart/form-data", headers=_auth())
        assert r_anon.status_code == 401
        assert r_auth.status_code not in (401, 403)

    def test_options_preflight_always_allowed(self, client):
        for path in [
            "/api/mass-appraisal/preview",
            "/api/mass-appraisal/run",
            "/api/mass-appraisal/export-xlsx",
            "/api/mass-appraisal/sales/verify",
            "/api/mass-appraisal/sales/time-adjust",
            "/api/mass-appraisal/sales/adjust",
            "/api/mass-appraisal/ratio-study/run",
            "/api/mass-appraisal/calibration/preview",
            "/api/mass-appraisal/calibration/sandbox",
            "/api/mass-appraisal/import-xlsx",
        ]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"


# ── Valuation pipeline ────────────────────────────────────────────────────────

class TestValuationPipelineAuthGated:

    def test_full_requires_auth(self, client):
        r_anon = client.post("/api/valuation/full", json={})
        r_auth = client.post("/api/valuation/full", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_report_requires_auth(self, client):
        r_anon = client.post("/api/valuation/report", json={})
        r_auth = client.post("/api/valuation/report", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_land_requires_auth(self, client):
        r_anon = client.post("/api/valuation/land", json={})
        r_auth = client.post("/api/valuation/land", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_audit_requires_auth(self, client):
        r_anon = client.post("/api/valuation/audit", json={})
        r_auth = client.post("/api/valuation/audit", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_portfolio_requires_auth(self, client):
        r_anon = client.post("/api/valuation/portfolio", json={})
        r_auth = client.post("/api/valuation/portfolio", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_portfolio_performance_requires_auth(self, client):
        r_anon = client.post("/api/valuation/portfolio/performance", json={})
        r_auth = client.post("/api/valuation/portfolio/performance", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_batch_post_requires_auth(self, client):
        r_anon = client.post("/api/valuation/batch", json={})
        r_auth = client.post("/api/valuation/batch", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_batch_get_requires_auth(self, client):
        r_anon = client.get("/api/valuation/batch")
        r_auth = client.get("/api/valuation/batch", headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_batch_status_requires_auth(self, client):
        r_anon = client.get("/api/valuation/batch/some-batch-id")
        r_auth = client.get("/api/valuation/batch/some-batch-id", headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_avm_requires_auth(self, client):
        r_anon = client.post("/api/valuation/avm", json={})
        r_auth = client.post("/api/valuation/avm", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_avm_batch_requires_auth(self, client):
        r_anon = client.post("/api/valuation/avm/batch", json={})
        r_auth = client.post("/api/valuation/avm/batch", json={}, headers=_auth())
        _assert_auth_gated(r_anon, r_auth)

    def test_options_preflight_always_allowed(self, client):
        for path in [
            "/api/valuation/full",
            "/api/valuation/report",
            "/api/valuation/land",
            "/api/valuation/audit",
            "/api/valuation/portfolio",
            "/api/valuation/portfolio/performance",
            "/api/valuation/batch",
            "/api/valuation/batch/some-id",
            "/api/valuation/avm",
            "/api/valuation/avm/batch",
        ]:
            r = client.options(path)
            assert r.status_code == 200, f"OPTIONS {path} returned {r.status_code}"
