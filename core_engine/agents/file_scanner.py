"""
file_scanner.py — Workspace File Scanner (Phase 17.0)

Scans a workspace directory and classifies files by type so the Expert Smart
agent knows which files contain property data, reports, or configuration.

Classes:
    FileType       — classification enum
    ScannedFile    — metadata record for one discovered file
    FileScanner    — scan, classify, and summarise workspace contents
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# ── File type enum ────────────────────────────────────────────────────────────


class FileType(str, Enum):
    PROPERTY_DATA = "property_data"  # .xlsx, .xls, .csv, .json
    REPORT = "report"  # .pdf, .docx (output reports)
    CONFIG = "config"  # .yaml, .yml, .toml, .ini, .env
    IMAGE = "image"  # .png, .jpg, .jpeg, .gif, .tiff
    UNKNOWN = "unknown"


# ── Extension maps ────────────────────────────────────────────────────────────

_PROPERTY_DATA_EXTS: frozenset = frozenset({".xlsx", ".xls", ".csv", ".json"})
_REPORT_EXTS: frozenset = frozenset({".pdf", ".docx", ".doc"})
_CONFIG_EXTS: frozenset = frozenset({".yaml", ".yml", ".toml", ".ini", ".env", ".cfg"})
_IMAGE_EXTS: frozenset = frozenset({".png", ".jpg", ".jpeg", ".gif", ".tiff", ".bmp"})


# ── Scanned file record ───────────────────────────────────────────────────────


@dataclass
class ScannedFile:
    """Metadata for a single file found during a workspace scan."""

    name: str
    relative_path: str
    absolute_path: str
    extension: str
    size_bytes: int
    modified_at: str
    file_type: str  # FileType value

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at,
            "file_type": self.file_type,
        }


# ── Scanner ───────────────────────────────────────────────────────────────────


class FileScanner:
    """
    Scan a directory tree and classify every file found.

    Designed to work with WorkspaceManager workspaces but accepts any
    absolute directory path.
    """

    # ── Classification ────────────────────────────────────────────────────────

    @staticmethod
    def classify_file(path: Path) -> str:
        """Return the FileType value for the given path (by extension)."""
        ext = path.suffix.lower()
        if ext in _PROPERTY_DATA_EXTS:
            return FileType.PROPERTY_DATA
        if ext in _REPORT_EXTS:
            return FileType.REPORT
        if ext in _CONFIG_EXTS:
            return FileType.CONFIG
        if ext in _IMAGE_EXTS:
            return FileType.IMAGE
        return FileType.UNKNOWN

    # ── Single-file builder ───────────────────────────────────────────────────

    @staticmethod
    def _scan_file(path: Path, root: Path) -> ScannedFile:
        stat = path.stat()
        return ScannedFile(
            name=path.name,
            relative_path=str(path.relative_to(root)),
            absolute_path=str(path),
            extension=path.suffix.lower(),
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            file_type=FileScanner.classify_file(path),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def scan_workspace(
        self,
        workspace_path: str,
        exclude_hidden: bool = True,
        max_depth: Optional[int] = None,
        skip_meta_file: str = "workspace.json",
    ) -> List[ScannedFile]:
        """
        Recursively scan workspace_path and return a ScannedFile list,
        sorted by relative_path.

        Parameters
        ----------
        workspace_path : absolute path to the workspace root
        exclude_hidden : skip files/dirs whose name starts with '.'
        max_depth      : maximum recursion depth (None = unlimited)
        skip_meta_file : filename to exclude (default: workspace.json)
        """
        root = Path(workspace_path).resolve()
        results: List[ScannedFile] = []

        def _walk(directory: Path, depth: int) -> None:
            if max_depth is not None and depth > max_depth:
                return
            try:
                entries = sorted(directory.iterdir())
            except PermissionError:
                return
            for entry in entries:
                if exclude_hidden and entry.name.startswith("."):
                    continue
                if entry.name == skip_meta_file:
                    continue
                if entry.is_dir():
                    _walk(entry, depth + 1)
                elif entry.is_file():
                    results.append(self._scan_file(entry, root))

        _walk(root, depth=0)
        return sorted(results, key=lambda f: f.relative_path)

    def find_property_files(self, workspace_path: str) -> List[ScannedFile]:
        """Return only files classified as PROPERTY_DATA."""
        return [f for f in self.scan_workspace(workspace_path) if f.file_type == FileType.PROPERTY_DATA]

    def get_workspace_stats(self, workspace_path: str) -> Dict:
        """
        Summarise the workspace contents.

        Returns
        -------
        dict with keys:
            total_files, total_size_bytes, by_type (counts per FileType),
            largest_file (ScannedFile dict or None),
            property_data_files (count of importable data files)
        """
        files = self.scan_workspace(workspace_path)

        by_type: Dict[str, int] = {ft.value: 0 for ft in FileType}
        total_size = 0
        largest: Optional[ScannedFile] = None

        for f in files:
            by_type[f.file_type] = by_type.get(f.file_type, 0) + 1
            total_size += f.size_bytes
            if largest is None or f.size_bytes > largest.size_bytes:
                largest = f

        return {
            "total_files": len(files),
            "total_size_bytes": total_size,
            "by_type": by_type,
            "largest_file": largest.to_dict() if largest else None,
            "property_data_files": by_type.get(FileType.PROPERTY_DATA, 0),
        }
