"""
pipeline_orchestrator.py — Automated Valuation Pipeline (Phase 18.0)

Reads property data files from a workspace, submits each record to the
Expert Smart valuation API, and writes a results CSV back to the workspace.

Supported input formats: CSV, JSON
Output: pipeline_results_<timestamp>.csv written into the workspace

Classes:
    PipelineStatus             — state machine enum
    PropertyRecord             — one parsed input property
    PipelineResult             — one valuation outcome
    PipelineReport             — aggregate summary + full results list
    ValuationPipelineOrchestrator — orchestrates scan → parse → valuate → save
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

# ── Status enum ───────────────────────────────────────────────────────────────


class PipelineStatus(str, Enum):
    IDLE = "idle"
    SCANNING = "scanning"
    PARSING = "parsing"
    VALUATING = "valuating"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @staticmethod
    def is_terminal(status: str) -> bool:
        return status in (
            PipelineStatus.COMPLETED,
            PipelineStatus.FAILED,
            PipelineStatus.CANCELLED,
        )


# ── Record / Result / Report dataclasses ─────────────────────────────────────


@dataclass
class PropertyRecord:
    """One property parsed from an input file."""

    record_id: str
    property_type: str
    area_sqm: float
    location: str
    source_file: str
    raw_data: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "record_id": self.record_id,
            "property_type": self.property_type,
            "area_sqm": self.area_sqm,
            "location": self.location,
            "source_file": self.source_file,
        }


@dataclass
class PipelineResult:
    """Valuation outcome for one PropertyRecord."""

    record_id: str
    property_type: str
    area_sqm: float
    location: str
    status: str  # "success" | "failed" | "skipped"
    primary_purpose: str
    valuation_value: Optional[float] = None
    error: Optional[str] = None
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "record_id": self.record_id,
            "property_type": self.property_type,
            "area_sqm": self.area_sqm,
            "location": self.location,
            "status": self.status,
            "primary_purpose": self.primary_purpose,
            "valuation_value": self.valuation_value,
            "error": self.error or "",
            "processed_at": self.processed_at,
        }


@dataclass
class PipelineReport:
    """Aggregate summary of a completed pipeline run."""

    pipeline_id: str
    workspace_id: str
    status: str
    total_records: int
    completed: int
    failed: int
    skipped: int
    total_valuation_value: float
    average_valuation: float
    started_at: str
    completed_at: Optional[str] = None
    output_file: Optional[str] = None
    results: List[PipelineResult] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "pipeline_id": self.pipeline_id,
            "workspace_id": self.workspace_id,
            "status": self.status,
            "total_records": self.total_records,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "total_valuation_value": self.total_valuation_value,
            "average_valuation": self.average_valuation,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "output_file": self.output_file,
        }


# ── Orchestrator ──────────────────────────────────────────────────────────────


class ValuationPipelineOrchestrator:
    """
    End-to-end valuation pipeline over a WorkspaceManager workspace.

    Parameters
    ----------
    workspace_manager : WorkspaceManager instance
    bridge            : ExpertSmartBridge instance (or any object with
                        an evaluate_property(area_sqm, location,
                        property_type, primary_purpose) method)
    """

    # CSV column name aliases (first match wins)
    _ID_COLS = ("property_id", "id", "record_id")
    _TYPE_COLS = ("property_type", "type", "prop_type")
    _AREA_COLS = ("area_sqm", "area", "sqm", "size")
    _LOC_COLS = ("location", "governorate", "city", "region")

    def __init__(self, workspace_manager: Any, bridge: Any) -> None:
        self._wm = workspace_manager
        self._bridge = bridge
        self._status = PipelineStatus.IDLE
        self._report: Optional[PipelineReport] = None

    # ── State ─────────────────────────────────────────────────────────────────

    def get_status(self) -> str:
        return self._status

    def get_report(self) -> Optional[PipelineReport]:
        return self._report

    def cancel(self) -> bool:
        """Request cancellation if the pipeline is not yet terminal."""
        if PipelineStatus.is_terminal(self._status):
            return False
        self._status = PipelineStatus.CANCELLED
        return True

    # ── Parsing helpers ───────────────────────────────────────────────────────

    @classmethod
    def _pick(cls, row: Dict, aliases: tuple, default: str = "") -> str:
        """Return the first alias key found in row (case-insensitive)."""
        row_lower = {k.lower(): v for k, v in row.items()}
        for alias in aliases:
            if alias in row_lower:
                return str(row_lower[alias]).strip()
        return default

    @classmethod
    def _parse_csv(cls, content: bytes, source_file: str) -> List[PropertyRecord]:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        records: List[PropertyRecord] = []
        for i, row in enumerate(reader):
            try:
                rid = cls._pick(row, cls._ID_COLS) or f"row_{i+1}"
                ptype = cls._pick(row, cls._TYPE_COLS) or "residential"
                loc = cls._pick(row, cls._LOC_COLS)
                area_raw = cls._pick(row, cls._AREA_COLS, "0")
                area = float(area_raw) if area_raw else 0.0
                if not loc or area <= 0:
                    continue  # skip invalid rows silently
                records.append(
                    PropertyRecord(
                        record_id=rid,
                        property_type=ptype,
                        area_sqm=area,
                        location=loc,
                        source_file=source_file,
                        raw_data=dict(row),
                    )
                )
            except (ValueError, TypeError):
                continue
        return records

    @classmethod
    def _parse_json(cls, content: bytes, source_file: str) -> List[PropertyRecord]:
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, dict):
            data = data.get("properties", [data])
        if not isinstance(data, list):
            return []
        records: List[PropertyRecord] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            try:
                rid = cls._pick(item, cls._ID_COLS) or f"item_{i+1}"
                ptype = cls._pick(item, cls._TYPE_COLS) or "residential"
                loc = cls._pick(item, cls._LOC_COLS)
                area_raw = cls._pick(item, cls._AREA_COLS, "0")
                area = float(area_raw) if area_raw else 0.0
                if not loc or area <= 0:
                    continue
                records.append(
                    PropertyRecord(
                        record_id=rid,
                        property_type=ptype,
                        area_sqm=area,
                        location=loc,
                        source_file=source_file,
                        raw_data=item,
                    )
                )
            except (ValueError, TypeError):
                continue
        return records

    def parse_file(self, workspace_id: str, relative_path: str) -> List[PropertyRecord]:
        """
        Parse one file from the workspace into PropertyRecord objects.
        Returns an empty list for unsupported extensions.
        """
        ext = Path(relative_path).suffix.lower()
        if ext not in (".csv", ".json"):
            return []
        content = self._wm.read_file(workspace_id, relative_path)
        if ext == ".csv":
            return self._parse_csv(content, relative_path)
        return self._parse_json(content, relative_path)

    def scan_workspace(self, workspace_id: str) -> List[PropertyRecord]:
        """
        Scan the workspace for CSV/JSON files and parse all of them.
        Files are processed in sorted order; duplicates share record_ids.
        """
        self._status = PipelineStatus.SCANNING
        files = self._wm.list_files(workspace_id, "**/*")
        self._status = PipelineStatus.PARSING
        records: List[PropertyRecord] = []
        for f in sorted(files):
            if Path(f).suffix.lower() in (".csv", ".json"):
                records.extend(self.parse_file(workspace_id, f))
        return records

    # ── Save ─────────────────────────────────────────────────────────────────

    def save_results(self, workspace_id: str, report: PipelineReport) -> str:
        """
        Write a results CSV into the workspace.
        Returns the relative path of the written file.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"pipeline_results_{ts}.csv"

        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=[
                "record_id",
                "property_type",
                "area_sqm",
                "location",
                "status",
                "primary_purpose",
                "valuation_value",
                "error",
                "processed_at",
            ],
        )
        writer.writeheader()
        for r in report.results:
            writer.writerow(r.to_dict())

        self._wm.write_file(workspace_id, name, buf.getvalue().encode("utf-8"))
        return name

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(
        self,
        workspace_id: str,
        primary_purpose: str = "market_value",
    ) -> PipelineReport:
        """
        Full pipeline: scan workspace → parse files → valuate each record
        → save results CSV → return PipelineReport.

        Errors on individual records are isolated — the pipeline continues.
        """
        pipeline_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()
        self._status = PipelineStatus.SCANNING

        report = PipelineReport(
            pipeline_id=pipeline_id,
            workspace_id=workspace_id,
            status=PipelineStatus.SCANNING,
            total_records=0,
            completed=0,
            failed=0,
            skipped=0,
            total_valuation_value=0.0,
            average_valuation=0.0,
            started_at=started_at,
        )
        self._report = report

        try:
            # 1 — scan + parse
            records = self.scan_workspace(workspace_id)
            report.total_records = len(records)

            if not records:
                report.status = PipelineStatus.COMPLETED
                report.completed_at = datetime.now().isoformat()
                self._status = PipelineStatus.COMPLETED
                return report

            # 2 — valuate
            self._status = PipelineStatus.VALUATING
            for rec in records:
                if self._status == PipelineStatus.CANCELLED:
                    result = PipelineResult(
                        record_id=rec.record_id,
                        property_type=rec.property_type,
                        area_sqm=rec.area_sqm,
                        location=rec.location,
                        status="skipped",
                        primary_purpose=primary_purpose,
                        error="pipeline cancelled",
                    )
                    report.results.append(result)
                    report.skipped += 1
                    continue

                try:
                    api_resp = self._bridge.evaluate_property(
                        rec.area_sqm,
                        rec.location,
                        rec.property_type,
                        primary_purpose,
                    )
                    if api_resp.success and api_resp.data:
                        val = float(
                            api_resp.data.get("primary_value")
                            or api_resp.data.get("final_value")
                            or api_resp.data.get("valuation_value")
                            or 0
                        )
                        result = PipelineResult(
                            record_id=rec.record_id,
                            property_type=rec.property_type,
                            area_sqm=rec.area_sqm,
                            location=rec.location,
                            status="success",
                            primary_purpose=primary_purpose,
                            valuation_value=val,
                        )
                        report.completed += 1
                        report.total_valuation_value += val
                    else:
                        result = PipelineResult(
                            record_id=rec.record_id,
                            property_type=rec.property_type,
                            area_sqm=rec.area_sqm,
                            location=rec.location,
                            status="failed",
                            primary_purpose=primary_purpose,
                            error=api_resp.error or "API returned non-success",
                        )
                        report.failed += 1

                except Exception as exc:
                    result = PipelineResult(
                        record_id=rec.record_id,
                        property_type=rec.property_type,
                        area_sqm=rec.area_sqm,
                        location=rec.location,
                        status="failed",
                        primary_purpose=primary_purpose,
                        error=str(exc),
                    )
                    report.failed += 1

                report.results.append(result)

            # 3 — aggregate
            if report.completed > 0:
                report.average_valuation = report.total_valuation_value / report.completed

            # 4 — save
            self._status = PipelineStatus.SAVING
            output = self.save_results(workspace_id, report)
            report.output_file = output

            report.status = PipelineStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()
            self._status = PipelineStatus.COMPLETED

        except Exception as exc:
            report.status = PipelineStatus.FAILED
            report.completed_at = datetime.now().isoformat()
            self._status = PipelineStatus.FAILED
            raise

        return report
