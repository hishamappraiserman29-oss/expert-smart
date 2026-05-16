"""Tests for tools/export_reports_json.py."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from core_engine.reports.db import save_report
from core_engine.reports.db.migrations import migrate

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "tools" / "export_reports_json.py"


def _run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=60,
    )


@pytest.fixture
def populated_db(tmp_path):
    db = tmp_path / "data.db"
    save_report({"x": 1}, profile_key="legacy", db_path=db,
                owner_user_id="alice")
    save_report({"y": 2}, profile_key="detailed", db_path=db,
                owner_user_id="bob", status="final")
    save_report({"z": 3}, profile_key="legacy", db_path=db,
                owner_user_id="alice", status="final")
    return db


class TestExport:
    def test_exports_all_by_default(self, populated_db, tmp_path):
        out = tmp_path / "export.json"
        r = _run(["--db", str(populated_db), "--out", str(out)])
        assert r.returncode == 0, r.stderr
        data = json.loads(out.read_text())
        assert data["count"] == 3

    def test_filter_by_profile(self, populated_db, tmp_path):
        out = tmp_path / "export.json"
        _run(["--db", str(populated_db), "--out", str(out),
              "--profile-key", "legacy"])
        data = json.loads(out.read_text())
        assert data["count"] == 2

    def test_filter_by_owner(self, populated_db, tmp_path):
        out = tmp_path / "export.json"
        _run(["--db", str(populated_db), "--out", str(out),
              "--owner-user-id", "alice"])
        data = json.loads(out.read_text())
        assert data["count"] == 2
        for r in data["records"]:
            assert r["owner_user_id"] == "alice"

    def test_filter_by_status(self, populated_db, tmp_path):
        out = tmp_path / "export.json"
        _run(["--db", str(populated_db), "--out", str(out),
              "--status", "final"])
        data = json.loads(out.read_text())
        assert data["count"] == 2

    def test_exclude_data_strips_payload(self, populated_db, tmp_path):
        out = tmp_path / "export.json"
        _run(["--db", str(populated_db), "--out", str(out),
              "--exclude-data"])
        data = json.loads(out.read_text())
        for r in data["records"]:
            assert "data" not in r

    def test_empty_db_count_zero(self, tmp_path):
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(db)
        migrate(conn)
        conn.close()
        out = tmp_path / "export.json"
        r = _run(["--db", str(db), "--out", str(out)])
        assert r.returncode == 0
        assert json.loads(out.read_text())["count"] == 0

    def test_arabic_content_preserved(self, tmp_path):
        db = tmp_path / "ar.db"
        save_report({"address": "القاهرة الجديدة"},
                    profile_key="legacy", db_path=db,
                    owner_user_id="alice")
        out = tmp_path / "export.json"
        _run(["--db", str(db), "--out", str(out)])
        # ensure_ascii=False => Arabic readable as-is
        raw = out.read_text(encoding="utf-8")
        assert "القاهرة" in raw

    def test_output_has_expected_top_level_keys(self, populated_db, tmp_path):
        out = tmp_path / "export.json"
        _run(["--db", str(populated_db), "--out", str(out)])
        data = json.loads(out.read_text())
        for key in ("exported_at", "filters", "count", "records"):
            assert key in data

    def test_records_have_all_columns(self, populated_db, tmp_path):
        out = tmp_path / "export.json"
        _run(["--db", str(populated_db), "--out", str(out)])
        data = json.loads(out.read_text())
        rec = data["records"][0]
        for col in ("report_id", "profile_key", "status", "owner_user_id",
                    "created_at", "updated_at", "data"):
            assert col in rec, f"missing column: {col}"

    def test_pretty_flag_produces_indented_json(self, populated_db, tmp_path):
        out = tmp_path / "export.json"
        _run(["--db", str(populated_db), "--out", str(out), "--pretty"])
        raw = out.read_text(encoding="utf-8")
        assert "\n" in raw  # indented JSON has newlines

    def test_out_parent_created_automatically(self, populated_db, tmp_path):
        out = tmp_path / "deep" / "nested" / "export.json"
        assert not out.parent.exists()
        r = _run(["--db", str(populated_db), "--out", str(out)])
        assert r.returncode == 0
        assert out.exists()

    def test_filter_owner_and_status_combined(self, populated_db, tmp_path):
        out = tmp_path / "export.json"
        _run(["--db", str(populated_db), "--out", str(out),
              "--owner-user-id", "alice", "--status", "final"])
        data = json.loads(out.read_text())
        assert data["count"] == 1
        assert data["records"][0]["owner_user_id"] == "alice"
        assert data["records"][0]["status"] == "final"
