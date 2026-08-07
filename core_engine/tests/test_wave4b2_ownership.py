"""Wave 4B2 tests — Mass Valuation run/prediction ownership boundary.

Closes OAF-004 (review referential-integrity) and OAF-005 (export ownership),
and proves the horizontal ownership boundary that Wave 4B1's admin-only gate
never addressed: two different admin identities must not be able to read,
review, or export each other's runs/predictions.

Ownership model (authoritative, see conversation authorization):
    non-admin caller           -> 403 (unchanged from Wave 4B1)
    same-owner admin           -> normal response
    different-owner admin      -> 404 (non-disclosing — same as unknown resource)
    unknown resource            -> 404
There is no admin ownership bypass.

Testing note — `core_engine/database/connection.py::get_db()` previously
lacked `@contextlib.contextmanager`, so every `with get_db() as db:` call
site in bridge_api.py raised TypeError before ever reaching a query. That
defect has since been fixed directly in `connection.py` (see
`test_database_connection.py` for dedicated coverage of `get_db()` itself).
These tests now exercise the real, unmodified production
`database.connection.get_db` context-manager implementation — only the
underlying session *provider* (`get_session_factory`) is monkeypatched to a
harmless fake, and the `mass_valuation.db_writer` query functions are
monkeypatched onto an in-memory store so the test suite is deterministic
without a live PostgreSQL instance. `get_db()` itself is never replaced or
wrapped.
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

_ORIG_CWD = os.getcwd()
try:
    os.chdir(str(_CORE))
    from bridge_api import app as _app
    import mass_valuation.db_writer as _mv_db
    import database.connection as _db_connection
finally:
    os.chdir(_ORIG_CWD)

_TEST_SECRET = "test-secret-wave4b2-ownership-min32!!"
_ADMIN_A = "admin-a-wave4b2"
_ADMIN_B = "admin-b-wave4b2"
_PLAIN_USER = "user-wave4b2"


def _make_token(user: str) -> str:
    from auth.tokens import generate_token
    return generate_token(user)


def _auth_header(user: str) -> dict:
    return {"Authorization": f"Bearer {_make_token(user)}"}


# ---------------------------------------------------------------------------
# Fake in-memory store — stands in for a real Postgres connection.
# Keyed exactly the way the real schema is: runs own predictions, predictions
# belong to exactly one run, review decisions reference both.
# ---------------------------------------------------------------------------

class _FakeSession:
    """Stands in for a SQLAlchemy Session so get_db()'s own close() call is safe."""

    def close(self):
        pass


class _FakeStore:
    def __init__(self):
        self.runs: dict = {}          # run_id -> {"created_by": ..., **fields}
        self.predictions: dict = {}   # prediction_id -> {"run_id": ..., **fields}
        self.reviews: list = []

    def add_run(self, run_id: str, created_by: str, **fields) -> None:
        self.runs[run_id] = {"run_id": run_id, "created_by": created_by, **fields}

    def add_prediction(self, prediction_id: str, run_id: str, **fields) -> None:
        self.predictions[prediction_id] = {
            "prediction_id": prediction_id, "run_id": run_id, **fields
        }


@pytest.fixture()
def store():
    return _FakeStore()


@pytest.fixture()
def mv_client(monkeypatch, store):
    """
    Test client with two configured admins (A and B), JWT auth. The real
    production `database.connection.get_db` context manager runs unmodified;
    only its underlying session provider is faked (no live PostgreSQL is
    available in this environment), and the Mass Valuation db_writer query
    functions are monkeypatched onto the in-memory fake store so ownership
    behavior is deterministic.
    """
    monkeypatch.setenv("JWT_SECRET", _TEST_SECRET)
    monkeypatch.setenv("ADMIN_USER_IDS", f"{_ADMIN_A},{_ADMIN_B}")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("AUDIT_ENABLED", "false")

    # get_db() itself is untouched — only the session it constructs is fake.
    monkeypatch.setattr(
        _db_connection, "get_session_factory", lambda: (lambda: _FakeSession())
    )

    def _fake_get_run_owner(run_id, db):
        run = store.runs.get(run_id)
        return run["created_by"] if run else None

    def _fake_get_prediction_run_id(prediction_id, db):
        pred = store.predictions.get(prediction_id)
        return pred["run_id"] if pred else None

    def _fake_get_predictions_for_run(run_id, db):
        return [p for p in store.predictions.values() if p["run_id"] == run_id]

    def _fake_list_runs(db, role="analyst", limit=50, owner_user_id=None):
        rows = list(store.runs.values())
        if owner_user_id is not None:
            rows = [r for r in rows if r["created_by"] == owner_user_id]
        return rows[:limit]

    def _fake_save_review_decision(
        prediction_id, run_id, decision, reason, reviewed_by, db,
        property_id="", model_value=None, reviewed_value=None,
    ):
        _mv_db._validate_reviewed_by(reviewed_by)
        _mv_db._validate_decision(decision)
        _mv_db._validate_reason(reason)
        store.reviews.append({
            "prediction_id": prediction_id, "run_id": run_id, "decision": decision,
        })
        return "fake-decision-id"

    def _fake_save_run(run_result, db):
        store.add_run(
            run_result["run_id"],
            run_result.get("created_by"),
            **{k: v for k, v in run_result.items() if k not in ("run_id", "created_by")},
        )
        return run_result["run_id"]

    monkeypatch.setattr(_mv_db, "get_run_owner", _fake_get_run_owner)
    monkeypatch.setattr(_mv_db, "get_prediction_run_id", _fake_get_prediction_run_id)
    monkeypatch.setattr(_mv_db, "get_predictions_for_run", _fake_get_predictions_for_run)
    monkeypatch.setattr(_mv_db, "list_runs", _fake_list_runs)
    monkeypatch.setattr(_mv_db, "save_review_decision", _fake_save_review_decision)
    monkeypatch.setattr(_mv_db, "save_run", _fake_save_run)

    _app.config["TESTING"] = True
    with _app.test_client() as c:
        yield c


@pytest.fixture()
def two_runs(store):
    """Run A owned by Admin A (with one prediction), Run B owned by Admin B (with one prediction)."""
    store.add_run("run-a", _ADMIN_A, run_name="Run A")
    store.add_run("run-b", _ADMIN_B, run_name="Run B")
    store.add_prediction("pred-a1", "run-a", property_id="PROP-A1")
    store.add_prediction("pred-b1", "run-b", property_id="PROP-B1")
    return store


# ── Run listing: owner-scoped ──────────────────────────────────────────────

def test_w2_01_admin_a_list_sees_only_run_a(mv_client, two_runs):
    rv = mv_client.get("/api/mass-valuation/runs", headers=_auth_header(_ADMIN_A))
    assert rv.status_code == 200
    run_ids = {r["run_id"] for r in rv.get_json()["runs"]}
    assert run_ids == {"run-a"}, f"Admin A must see only Run A, got {run_ids}"


def test_w2_02_admin_b_list_sees_only_run_b(mv_client, two_runs):
    rv = mv_client.get("/api/mass-valuation/runs", headers=_auth_header(_ADMIN_B))
    assert rv.status_code == 200
    run_ids = {r["run_id"] for r in rv.get_json()["runs"]}
    assert run_ids == {"run-b"}, f"Admin B must see only Run B, got {run_ids}"


def test_w2_03_non_admin_list_returns_403(mv_client, two_runs):
    rv = mv_client.get("/api/mass-valuation/runs", headers=_auth_header(_PLAIN_USER))
    assert rv.status_code == 403


# ── Prediction retrieval: owner-scoped ─────────────────────────────────────

def test_w2_04_admin_a_reads_own_run_predictions_allowed(mv_client, two_runs):
    rv = mv_client.get(
        "/api/mass-valuation/predictions/run-a", headers=_auth_header(_ADMIN_A)
    )
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["count"] == 1
    assert body["predictions"][0]["prediction_id"] == "pred-a1"


def test_w2_05_admin_a_reads_run_b_predictions_returns_404(mv_client, two_runs):
    rv = mv_client.get(
        "/api/mass-valuation/predictions/run-b", headers=_auth_header(_ADMIN_A)
    )
    assert rv.status_code == 404, (
        f"Admin A reading Run B's predictions must be 404 (non-disclosing), got {rv.status_code}"
    )


def test_w2_06_admin_b_reads_run_a_predictions_returns_404(mv_client, two_runs):
    rv = mv_client.get(
        "/api/mass-valuation/predictions/run-a", headers=_auth_header(_ADMIN_B)
    )
    assert rv.status_code == 404


def test_w2_07_admin_reads_unknown_run_returns_404(mv_client, two_runs):
    rv = mv_client.get(
        "/api/mass-valuation/predictions/does-not-exist", headers=_auth_header(_ADMIN_A)
    )
    assert rv.status_code == 404


def test_w2_08_unknown_and_wrong_owner_are_the_same_status(mv_client, two_runs):
    """Non-disclosing: a caller must not be able to tell 'wrong owner' from 'never existed'."""
    rv_wrong_owner = mv_client.get(
        "/api/mass-valuation/predictions/run-b", headers=_auth_header(_ADMIN_A)
    )
    rv_unknown = mv_client.get(
        "/api/mass-valuation/predictions/totally-unknown-id", headers=_auth_header(_ADMIN_A)
    )
    assert rv_wrong_owner.status_code == rv_unknown.status_code == 404


def test_w2_09_non_admin_predictions_still_403(mv_client, two_runs):
    rv = mv_client.get(
        "/api/mass-valuation/predictions/run-a", headers=_auth_header(_PLAIN_USER)
    )
    assert rv.status_code == 403


# ── Review integrity: prediction/run/owner relationship ───────────────────

def test_w2_10_admin_a_reviews_own_prediction_allowed(mv_client, two_runs):
    rv = mv_client.post(
        "/api/mass-valuation/review/pred-a1",
        json={"run_id": "run-a", "decision": "accepted", "reason": "Verified"},
        headers=_auth_header(_ADMIN_A),
    )
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json()["db_persisted"] is True


def test_w2_11_admin_a_reviews_run_b_prediction_returns_404(mv_client, two_runs):
    """Admin A must not review a prediction belonging to Run B, even by supplying Run B's own run_id."""
    rv = mv_client.post(
        "/api/mass-valuation/review/pred-b1",
        json={"run_id": "run-b", "decision": "accepted", "reason": "Verified"},
        headers=_auth_header(_ADMIN_A),
    )
    assert rv.status_code == 404


def test_w2_12_mismatched_prediction_run_relationship_rejected(mv_client, two_runs):
    """pred-a1 actually belongs to run-a; supplying run-b must be rejected, not silently accepted."""
    rv = mv_client.post(
        "/api/mass-valuation/review/pred-a1",
        json={"run_id": "run-b", "decision": "accepted", "reason": "Verified"},
        headers=_auth_header(_ADMIN_A),
    )
    assert rv.status_code == 404, (
        "A prediction_id/run_id pair that does not match the real parent-run "
        "relationship must be rejected, not persisted"
    )


def test_w2_13_review_unknown_prediction_returns_404(mv_client, two_runs):
    rv = mv_client.post(
        "/api/mass-valuation/review/does-not-exist",
        json={"run_id": "run-a", "decision": "accepted", "reason": "Verified"},
        headers=_auth_header(_ADMIN_A),
    )
    assert rv.status_code == 404


def test_w2_14_non_admin_review_still_403(mv_client, two_runs):
    rv = mv_client.post(
        "/api/mass-valuation/review/pred-a1",
        json={"run_id": "run-a", "decision": "accepted", "reason": "Verified"},
        headers=_auth_header(_PLAIN_USER),
    )
    assert rv.status_code == 403


# ── Export: owner-scoped, still admin-only, still a stub ──────────────────

def test_w2_15_admin_a_export_own_run_authorized_stub(mv_client, two_runs):
    rv = mv_client.get(
        "/api/mass-valuation/runs/run-a/export", headers=_auth_header(_ADMIN_A)
    )
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["status"] == "not_generated", (
        "Wave 4B2 does not implement export generation — must remain the existing stub"
    )


def test_w2_16_admin_a_export_run_b_returns_404(mv_client, two_runs):
    rv = mv_client.get(
        "/api/mass-valuation/runs/run-b/export", headers=_auth_header(_ADMIN_A)
    )
    assert rv.status_code == 404


def test_w2_17_non_admin_export_still_403(mv_client, two_runs):
    rv = mv_client.get(
        "/api/mass-valuation/runs/run-a/export", headers=_auth_header(_PLAIN_USER)
    )
    assert rv.status_code == 403


# ── Legacy ownership policy: created_by IS NULL rows (pre-dating Wave 4B2) ─
#
# LEGACY_RUN_OWNERSHIP_POLICY = HIDE_UNOWNED_LEGACY_ROWS_NO_AUTO_CLAIM.
# A run persisted before Wave 4B2 started populating created_by has
# created_by=NULL. It must not be auto-claimed by whichever admin happens to
# call an endpoint, must not be exposed via any owner-scoped read, and must
# never be silently assigned an owner as a side effect of any request.

@pytest.fixture()
def legacy_run(two_runs):
    """Run C: pre-Wave-4B2 row with created_by=NULL, alongside Run A / Run B."""
    two_runs.add_run("run-legacy", None, run_name="Legacy Run (pre-4B2)")
    two_runs.add_prediction("pred-legacy1", "run-legacy", property_id="PROP-LEGACY")
    return two_runs


def test_w2_20_legacy_null_owner_run_absent_from_admin_a_list(mv_client, legacy_run):
    rv = mv_client.get("/api/mass-valuation/runs", headers=_auth_header(_ADMIN_A))
    assert rv.status_code == 200
    run_ids = {r["run_id"] for r in rv.get_json()["runs"]}
    assert "run-legacy" not in run_ids


def test_w2_21_legacy_null_owner_run_absent_from_admin_b_list(mv_client, legacy_run):
    rv = mv_client.get("/api/mass-valuation/runs", headers=_auth_header(_ADMIN_B))
    assert rv.status_code == 200
    run_ids = {r["run_id"] for r in rv.get_json()["runs"]}
    assert "run-legacy" not in run_ids


def test_w2_22_legacy_null_owner_predictions_return_404_for_admin_a(mv_client, legacy_run):
    rv = mv_client.get(
        "/api/mass-valuation/predictions/run-legacy", headers=_auth_header(_ADMIN_A)
    )
    assert rv.status_code == 404


def test_w2_23_legacy_null_owner_predictions_return_404_for_admin_b(mv_client, legacy_run):
    rv = mv_client.get(
        "/api/mass-valuation/predictions/run-legacy", headers=_auth_header(_ADMIN_B)
    )
    assert rv.status_code == 404


def test_w2_24_legacy_null_owner_review_returns_404(mv_client, legacy_run):
    rv = mv_client.post(
        "/api/mass-valuation/review/pred-legacy1",
        json={"run_id": "run-legacy", "decision": "accepted", "reason": "Verified"},
        headers=_auth_header(_ADMIN_A),
    )
    assert rv.status_code == 404


def test_w2_25_legacy_null_owner_export_returns_404(mv_client, legacy_run):
    rv = mv_client.get(
        "/api/mass-valuation/runs/run-legacy/export", headers=_auth_header(_ADMIN_A)
    )
    assert rv.status_code == 404


def test_w2_26_legacy_run_created_by_not_mutated_by_any_request(mv_client, legacy_run):
    """No amount of admin traffic against the legacy run may assign it an owner."""
    mv_client.get("/api/mass-valuation/predictions/run-legacy", headers=_auth_header(_ADMIN_A))
    mv_client.get("/api/mass-valuation/predictions/run-legacy", headers=_auth_header(_ADMIN_B))
    mv_client.post(
        "/api/mass-valuation/review/pred-legacy1",
        json={"run_id": "run-legacy", "decision": "accepted", "reason": "Verified"},
        headers=_auth_header(_ADMIN_A),
    )
    mv_client.get("/api/mass-valuation/runs/run-legacy/export", headers=_auth_header(_ADMIN_A))
    assert legacy_run.runs["run-legacy"]["created_by"] is None


def test_w2_27_legacy_run_still_present_in_store_not_deleted(mv_client, legacy_run):
    """Hidden means inaccessible through owner-scoped paths — not deleted."""
    mv_client.get("/api/mass-valuation/predictions/run-legacy", headers=_auth_header(_ADMIN_A))
    assert "run-legacy" in legacy_run.runs


# ── Forged created_by: caller-supplied body value must have no effect ─────
# R3 closure (1/3): the prior code review flagged that no test proved a
# client-supplied `created_by` field in the request body is ignored. The
# route code never reads `body.get("created_by")` (verified by inspection),
# but this test proves it at the HTTP boundary — through the real
# `mv_run()` route — rather than relying on inspection alone.

_MIN_VALID_RECORD = {
    "property_id":       "PROP-FORGE-001",
    "property_type":     "residential",
    "city":              "Riyadh",
    "district":          "Al Nakheel",
    "land_area_m2":      300.0,
    "built_up_area_m2":  200.0,
    "transaction_date":  "2024-01-15",
    "transaction_price": 2_000_000,
    "evidence_type":     "registered_sale",
    "age":               5,
    "condition":         "good",
    "use":               "owner_occupied",
    "quality_finish":    "standard",
    "latitude":          24.7136,
    "longitude":         46.6753,
}


def test_w2_28_forged_created_by_in_request_body_is_ignored(mv_client, store):
    """A client that sends created_by=<someone else> in the POST body must be overridden by g.user_id."""
    rv = mv_client.post(
        "/api/mass-valuation/run",
        json={
            "records": [_MIN_VALID_RECORD],
            "run_name": "Forgery attempt",
            "created_by": _ADMIN_B,  # forged — Admin A is the actual authenticated caller
        },
        headers=_auth_header(_ADMIN_A),
    )
    assert rv.status_code == 200, rv.get_json()
    run_id = rv.get_json()["run_id"]
    assert store.runs[run_id]["created_by"] == _ADMIN_A, (
        "created_by must be the authenticated caller (Admin A), "
        "never a value taken from the request body"
    )
    assert store.runs[run_id]["created_by"] != _ADMIN_B


# ── Run creation: created_by stamping (constructor-level, no DB needed) ───

def test_w2_18_runner_stamps_created_by_from_constructor():
    from mass_valuation.runner import MassValuationRunner
    runner = MassValuationRunner(created_by=_ADMIN_A)
    result = runner.run([])
    assert result["created_by"] == _ADMIN_A


def test_w2_19_runner_created_by_defaults_to_none_when_unset():
    from mass_valuation.runner import MassValuationRunner
    runner = MassValuationRunner()
    result = runner.run([])
    assert result["created_by"] is None


# ── Method/source provenance for non-"avm" methods ─────────────────────────
# R3 closure (3/3): the prior code review flagged that _model_version_for_method()'s
# "comparable" and blended branches had zero direct output-value test coverage —
# every existing fixture only ever used the literal "hedonic-v1" as static data,
# never as an assertion produced by a non-default-method run.

def test_w2_29_avm_method_uses_hedonic_v1_model_version():
    from mass_valuation.runner import MassValuationRunner
    result = MassValuationRunner(method="avm").run([_MIN_VALID_RECORD])
    preds = result.get("predictions", [])
    assert preds, "expected at least one prediction for a valid input record"
    for p in preds:
        assert p["model_version"] == "hedonic-v1"
        assert p["source_method"] == "avm"


def test_w2_30_comparable_method_uses_comparable_v1_model_version():
    from mass_valuation.runner import MassValuationRunner
    result = MassValuationRunner(method="comparable").run([_MIN_VALID_RECORD])
    preds = result.get("predictions", [])
    assert preds
    for p in preds:
        assert p["model_version"] == "comparable-v1", (
            f"comparable method must not be falsely labeled hedonic-v1, got {p['model_version']!r}"
        )
        assert p["source_method"] == "comparable"


def test_w2_31_both_method_uses_blended_model_version():
    from mass_valuation.runner import MassValuationRunner
    result = MassValuationRunner(method="both").run([_MIN_VALID_RECORD])
    preds = result.get("predictions", [])
    assert preds
    for p in preds:
        assert p["model_version"] == "hedonic-comparable-blend-v1", (
            f"blended method must not be falsely labeled hedonic-v1, got {p['model_version']!r}"
        )
        assert p["source_method"] == "both"


def test_w2_32_run_level_method_field_matches_constructor_for_all_three_methods():
    from mass_valuation.runner import MassValuationRunner
    for method in ("avm", "comparable", "both"):
        result = MassValuationRunner(method=method).run([_MIN_VALID_RECORD])
        assert result["method"] == method
