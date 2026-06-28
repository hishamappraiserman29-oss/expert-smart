# -*- coding: utf-8 -*-
"""
tax_appeal_structured_parser.py — Structured parser for Excel/CSV comparables.

Purpose:
  Parse Excel/CSV comparables files into advisory candidate summaries without OCR.
  This is a controlled advisory-only pilot for:
    - market_comparables_excel
    - rental_comparables_excel
    - tax_comparables_excel

Safety invariants (always enforced):
  production_ready          = False
  accepted_by_default       = False
  needs_human_review        = True
  certified_usage_allowed   = False
  preliminary_visible       = True
  expert_review_visible     = True
  external_api_used         = False
  qdrant_used               = False
  rag_used                  = False

Advisory label:
  "استخلاص جدولي مبدئي — غير معتمد"
"""
from __future__ import annotations

import csv
import io
import statistics
import uuid
from pathlib import Path
from typing import Optional

# ── Supported evidence types ──────────────────────────────────────────────────

STRUCTURED_EVIDENCE_TYPES: frozenset[str] = frozenset({
    "market_comparables_excel",
    "rental_comparables_excel",
    "tax_comparables_excel",
})

# ── Advisory label ────────────────────────────────────────────────────────────

ADVISORY_LABEL_AR = "استخلاص جدولي مبدئي — غير معتمد"

# ── Column alias maps ─────────────────────────────────────────────────────────

# Each alias maps to a canonical column name.  Multiple Arabic + English
# variants are accepted; all are lowercased + stripped before lookup.

_MARKET_ALIASES: dict[str, str] = {
    # comparable_id
    "comparable_id": "comparable_id",
    "رقم المقارن": "comparable_id",
    "رقم": "comparable_id",
    "id": "comparable_id",
    # district
    "district": "district",
    "المنطقة": "district",
    "منطقة": "district",
    "الحي": "district",
    # property_type
    "property_type": "property_type",
    "نوع العقار": "property_type",
    "نوع": "property_type",
    # area_m2
    "area_m2": "area_m2",
    "المساحة": "area_m2",
    "مساحة": "area_m2",
    "area": "area_m2",
    "م2": "area_m2",
    "م²": "area_m2",
    # sale_price
    "sale_price": "sale_price",
    "سعر البيع": "sale_price",
    "سعر": "sale_price",
    "price": "sale_price",
    # price_per_m2
    "price_per_m2": "price_per_m2",
    "سعر المتر": "price_per_m2",
    "سعر/م": "price_per_m2",
    "price/m2": "price_per_m2",
    # transaction_date
    "transaction_date": "transaction_date",
    "تاريخ الصفقة": "transaction_date",
    "تاريخ": "transaction_date",
    "date": "transaction_date",
    # adjustment_percent
    "adjustment_percent": "adjustment_percent",
    "نسبة التعديل": "adjustment_percent",
    "تعديل%": "adjustment_percent",
    "adj%": "adjustment_percent",
    # adjusted_price_per_m2
    "adjusted_price_per_m2": "adjusted_price_per_m2",
    "سعر المتر المعدل": "adjusted_price_per_m2",
    "adj_price/m2": "adjusted_price_per_m2",
    # source_note
    "source_note": "source_note",
    "المصدر": "source_note",
    "مصدر": "source_note",
    "source": "source_note",
}

_RENTAL_ALIASES: dict[str, str] = {
    "comparable_id": "comparable_id",
    "رقم المقارن": "comparable_id",
    "رقم": "comparable_id",
    "id": "comparable_id",
    "district": "district",
    "المنطقة": "district",
    "منطقة": "district",
    "الحي": "district",
    "property_type": "property_type",
    "نوع العقار": "property_type",
    "نوع": "property_type",
    "area_m2": "area_m2",
    "المساحة": "area_m2",
    "مساحة": "area_m2",
    "area": "area_m2",
    "م2": "area_m2",
    "م²": "area_m2",
    "monthly_rent": "monthly_rent",
    "الإيجار الشهري": "monthly_rent",
    "إيجار شهري": "monthly_rent",
    "monthly": "monthly_rent",
    "annual_rent": "annual_rent",
    "الإيجار السنوي": "annual_rent",
    "إيجار سنوي": "annual_rent",
    "annual": "annual_rent",
    "rent_per_m2": "rent_per_m2",
    "إيجار المتر": "rent_per_m2",
    "إيجار/م": "rent_per_m2",
    "rent/m2": "rent_per_m2",
    "lease_date": "lease_date",
    "تاريخ الإيجار": "lease_date",
    "تاريخ": "lease_date",
    "date": "lease_date",
    "adjustment_percent": "adjustment_percent",
    "نسبة التعديل": "adjustment_percent",
    "تعديل%": "adjustment_percent",
    "adj%": "adjustment_percent",
    "adjusted_rent_per_m2": "adjusted_rent_per_m2",
    "إيجار المتر المعدل": "adjusted_rent_per_m2",
    "adj_rent/m2": "adjusted_rent_per_m2",
    "source_note": "source_note",
    "المصدر": "source_note",
    "مصدر": "source_note",
    "source": "source_note",
}

_TAX_ALIASES: dict[str, str] = {
    "comparable_id": "comparable_id",
    "رقم المقارن": "comparable_id",
    "رقم": "comparable_id",
    "id": "comparable_id",
    "district": "district",
    "المنطقة": "district",
    "منطقة": "district",
    "الحي": "district",
    "property_type": "property_type",
    "نوع العقار": "property_type",
    "نوع": "property_type",
    "area_m2": "area_m2",
    "المساحة": "area_m2",
    "مساحة": "area_m2",
    "area": "area_m2",
    "م2": "area_m2",
    "م²": "area_m2",
    "annual_tax": "annual_tax",
    "الضريبة السنوية": "annual_tax",
    "ضريبة سنوية": "annual_tax",
    "annual_tax_egp": "annual_tax",
    "tax_per_m2": "tax_per_m2",
    "ضريبة المتر": "tax_per_m2",
    "ضريبة/م": "tax_per_m2",
    "tax/m2": "tax_per_m2",
    "assessment_year": "assessment_year",
    "سنة الحصر": "assessment_year",
    "سنة": "assessment_year",
    "year": "assessment_year",
    "tax_authority": "tax_authority",
    "المأمورية": "tax_authority",
    "مأمورية": "tax_authority",
    "authority": "tax_authority",
    "adjustment_percent": "adjustment_percent",
    "نسبة التعديل": "adjustment_percent",
    "تعديل%": "adjustment_percent",
    "adj%": "adjustment_percent",
    "adjusted_tax_per_m2": "adjusted_tax_per_m2",
    "ضريبة المتر المعدلة": "adjusted_tax_per_m2",
    "adj_tax/m2": "adjusted_tax_per_m2",
    "source_note": "source_note",
    "المصدر": "source_note",
    "مصدر": "source_note",
    "source": "source_note",
}

# Required columns per evidence type (advisory — missing ones produce warnings)
_REQUIRED_COLUMNS: dict[str, list[str]] = {
    "market_comparables_excel": ["area_m2", "price_per_m2"],
    "rental_comparables_excel": ["area_m2", "rent_per_m2"],
    "tax_comparables_excel":    ["area_m2", "tax_per_m2"],
}

_ALIAS_MAP: dict[str, dict[str, str]] = {
    "market_comparables_excel": _MARKET_ALIASES,
    "rental_comparables_excel": _RENTAL_ALIASES,
    "tax_comparables_excel":    _TAX_ALIASES,
}


# ── ID helpers ────────────────────────────────────────────────────────────────

def _new_parse_job_id() -> str:
    return "SP-" + uuid.uuid4().hex[:8].upper()


# ── Safe result builder ───────────────────────────────────────────────────────

def _base_result(parse_job_id: str, evidence_id: str, request_id: str,
                 evidence_type: str) -> dict:
    return {
        "parse_job_id":               parse_job_id,
        "evidence_id":                evidence_id,
        "request_id":                 request_id,
        "evidence_type":              evidence_type,
        "parser_name":                "structured_parser_advisory",
        "parser_available":           False,
        "input_file_type":            None,
        "sheet_names":                [],
        "detected_columns":           [],
        "normalized_columns":         [],
        "row_count":                  0,
        "usable_row_count":           0,
        "rejected_row_count":         0,
        "candidate_summary":          {},
        "candidate_rows_preview":     [],
        "warnings":                   [],
        "errors":                     [],
        "external_api_used":          False,
        "qdrant_used":                False,
        "rag_used":                   False,
        "production_ready":           False,
        "accepted_by_default":        False,
        "needs_human_review":         True,
        "certified_usage_allowed":    False,
        "preliminary_visible":        True,
        "expert_review_visible":      True,
        "advisory_label_ar":          ADVISORY_LABEL_AR,
        "advisory_source_type":       "structured_parser",
    }


def _enforce_invariants(result: dict) -> dict:
    result["external_api_used"]       = False
    result["qdrant_used"]             = False
    result["rag_used"]                = False
    result["production_ready"]        = False
    result["accepted_by_default"]     = False
    result["needs_human_review"]      = True
    result["certified_usage_allowed"] = False
    result["advisory_label_ar"]       = ADVISORY_LABEL_AR
    return result


# ── Column normalization ──────────────────────────────────────────────────────

def _normalize_col(raw: str, aliases: dict[str, str]) -> Optional[str]:
    """Map a raw column header to its canonical name, or None if unknown."""
    key = raw.strip().lower()
    # Direct lookup
    if key in aliases:
        return aliases[key]
    # Try with full-width space collapse
    key2 = " ".join(key.split())
    return aliases.get(key2)


def normalize_columns(raw_headers: list[str],
                      evidence_type: str) -> tuple[list[str], list[str], list[str]]:
    """
    Normalize raw column headers.

    Returns:
        (detected_columns, normalized_columns, unknown_columns)
    """
    aliases = _ALIAS_MAP.get(evidence_type, {})
    detected: list[str] = []
    normalized: list[str] = []
    unknown: list[str] = []
    seen_canonical: set[str] = set()

    for raw in raw_headers:
        canonical = _normalize_col(raw, aliases)
        if canonical and canonical not in seen_canonical:
            detected.append(raw)
            normalized.append(canonical)
            seen_canonical.add(canonical)
        else:
            unknown.append(raw)

    return detected, normalized, unknown


# ── Row parsing ───────────────────────────────────────────────────────────────

def _parse_float(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        f = float(val)
        return f if (f == f and abs(f) < 1e15) else None  # reject NaN / inf
    s = str(val).strip().replace(",", "").replace(" ", "")
    if not s or s in ("-", "—", "N/A", "n/a", ""):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_rows(rows: list[dict], normalized_columns: list[str]) -> tuple[list[dict], list[dict]]:
    """Return (usable_rows, rejected_rows). usable = at least one numeric field."""
    usable: list[dict] = []
    rejected: list[dict] = []
    numeric_keys = {
        "area_m2", "sale_price", "price_per_m2", "adjustment_percent",
        "adjusted_price_per_m2", "monthly_rent", "annual_rent", "rent_per_m2",
        "adjusted_rent_per_m2", "annual_tax", "tax_per_m2", "adjusted_tax_per_m2",
    }
    for row in rows:
        has_numeric = any(
            _parse_float(row.get(c)) is not None
            for c in normalized_columns
            if c in numeric_keys
        )
        if has_numeric:
            usable.append(row)
        else:
            rejected.append(row)
    return usable, rejected


# ── Candidate summary builders ────────────────────────────────────────────────

def _safe_stats(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "min": None, "max": None, "average": None, "median": None}
    return {
        "count":   len(values),
        "min":     round(min(values), 2),
        "max":     round(max(values), 2),
        "average": round(statistics.mean(values), 2),
        "median":  round(statistics.median(values), 2),
    }


def _district_summary(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        d = str(row.get("district") or "غير محدد").strip()
        counts[d] = counts.get(d, 0) + 1
    return counts


def _date_range(rows: list[dict], date_col: str) -> dict:
    dates = [str(row[date_col]).strip() for row in rows
             if row.get(date_col) and str(row.get(date_col, "")).strip()]
    if not dates:
        return {"earliest": None, "latest": None, "count": 0}
    dates_sorted = sorted(dates)
    return {"earliest": dates_sorted[0], "latest": dates_sorted[-1], "count": len(dates)}


def _source_quality_note(usable_count: int, total_count: int, warnings: list[str]) -> str:
    if total_count == 0:
        return "لا توجد بيانات قابلة للاستخراج."
    ratio = usable_count / total_count
    if ratio >= 0.8 and not warnings:
        return "جودة البيانات جيدة — معظم الصفوف قابلة للاستخدام."
    elif ratio >= 0.5:
        return f"جودة البيانات متوسطة — {usable_count} من {total_count} صف صالح."
    else:
        return f"جودة البيانات منخفضة — {usable_count} من {total_count} فقط. مراجعة الخبير ضرورية."


def _build_market_summary(usable_rows: list[dict], normalized_cols: list[str]) -> dict:
    ppm2 = [_parse_float(r.get("price_per_m2")) for r in usable_rows]
    ppm2 = [v for v in ppm2 if v is not None and v > 0]

    adj_ppm2 = [_parse_float(r.get("adjusted_price_per_m2")) for r in usable_rows]
    adj_ppm2 = [v for v in adj_ppm2 if v is not None and v > 0]

    summary: dict = {
        "comparable_count":              len(usable_rows),
        "usable_row_count":              len(usable_rows),
        "price_per_m2_stats":            _safe_stats(ppm2),
        "average_price_per_m2":          round(statistics.mean(ppm2), 2) if ppm2 else None,
        "min_price_per_m2":              round(min(ppm2), 2) if ppm2 else None,
        "max_price_per_m2":              round(max(ppm2), 2) if ppm2 else None,
        "median_price_per_m2":           round(statistics.median(ppm2), 2) if ppm2 else None,
        "average_adjusted_price_per_m2": round(statistics.mean(adj_ppm2), 2) if adj_ppm2 else None,
        "reference_date_range":          _date_range(usable_rows, "transaction_date"),
        "district_summary":              _district_summary(usable_rows),
    }
    return summary


def _build_rental_summary(usable_rows: list[dict], normalized_cols: list[str]) -> dict:
    rpm2 = [_parse_float(r.get("rent_per_m2")) for r in usable_rows]
    rpm2 = [v for v in rpm2 if v is not None and v > 0]

    monthly = [_parse_float(r.get("monthly_rent")) for r in usable_rows]
    monthly = [v for v in monthly if v is not None and v > 0]

    annual = [_parse_float(r.get("annual_rent")) for r in usable_rows]
    annual = [v for v in annual if v is not None and v > 0]

    adj_rpm2 = [_parse_float(r.get("adjusted_rent_per_m2")) for r in usable_rows]
    adj_rpm2 = [v for v in adj_rpm2 if v is not None and v > 0]

    summary: dict = {
        "comparable_count":               len(usable_rows),
        "usable_row_count":               len(usable_rows),
        "rent_per_m2_stats":              _safe_stats(rpm2),
        "average_rent_per_m2":            round(statistics.mean(rpm2), 2) if rpm2 else None,
        "min_rent_per_m2":                round(min(rpm2), 2) if rpm2 else None,
        "max_rent_per_m2":                round(max(rpm2), 2) if rpm2 else None,
        "median_rent_per_m2":             round(statistics.median(rpm2), 2) if rpm2 else None,
        "average_monthly_rent":           round(statistics.mean(monthly), 2) if monthly else None,
        "average_annual_rent":            round(statistics.mean(annual), 2) if annual else None,
        "average_adjusted_rent_per_m2":   round(statistics.mean(adj_rpm2), 2) if adj_rpm2 else None,
        "reference_date_range":           _date_range(usable_rows, "lease_date"),
        "district_summary":               _district_summary(usable_rows),
    }
    return summary


def _build_tax_summary(usable_rows: list[dict], normalized_cols: list[str]) -> dict:
    tpm2 = [_parse_float(r.get("tax_per_m2")) for r in usable_rows]
    tpm2 = [v for v in tpm2 if v is not None and v > 0]

    adj_tpm2 = [_parse_float(r.get("adjusted_tax_per_m2")) for r in usable_rows]
    adj_tpm2 = [v for v in adj_tpm2 if v is not None and v > 0]

    years = [str(r.get("assessment_year") or "").strip() for r in usable_rows
             if r.get("assessment_year") and str(r.get("assessment_year", "")).strip()]

    summary: dict = {
        "comparable_count":               len(usable_rows),
        "usable_row_count":               len(usable_rows),
        "tax_per_m2_stats":               _safe_stats(tpm2),
        "average_tax_per_m2":             round(statistics.mean(tpm2), 2) if tpm2 else None,
        "min_tax_per_m2":                 round(min(tpm2), 2) if tpm2 else None,
        "max_tax_per_m2":                 round(max(tpm2), 2) if tpm2 else None,
        "median_tax_per_m2":              round(statistics.median(tpm2), 2) if tpm2 else None,
        "average_adjusted_tax_per_m2":    round(statistics.mean(adj_tpm2), 2) if adj_tpm2 else None,
        "assessment_year_range": {
            "earliest": min(years) if years else None,
            "latest":   max(years) if years else None,
            "count":    len(years),
        },
        "district_summary":               _district_summary(usable_rows),
    }
    return summary


_SUMMARY_BUILDERS = {
    "market_comparables_excel": _build_market_summary,
    "rental_comparables_excel": _build_rental_summary,
    "tax_comparables_excel":    _build_tax_summary,
}


# ── Excel reader ──────────────────────────────────────────────────────────────

def _read_excel_rows(file_path: Path) -> tuple[list[str], list[list], list[str], list[str]]:
    """
    Read an Excel/XLSX file.

    Returns (raw_headers, data_rows_as_lists, sheet_names, errors)
    Uses openpyxl (already a dependency via tax_appeal_workbook_builder).
    Handles .xlsx and .xls (if openpyxl supports it).
    """
    errors: list[str] = []
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
        sheet_names = wb.sheetnames
        ws = wb.active
        if ws is None:
            errors.append("لا يوجد ورقة نشطة في الملف.")
            return [], [], sheet_names, errors
        all_rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not all_rows:
            errors.append("الملف فارغ أو لا يحتوي صفوفاً.")
            return [], [], sheet_names, errors
        raw_headers = [str(c) if c is not None else "" for c in all_rows[0]]
        data_rows = [list(row) for row in all_rows[1:]]
        return raw_headers, data_rows, sheet_names, errors
    except ImportError:
        errors.append("مكتبة openpyxl غير متاحة — لا يمكن قراءة Excel.")
        return [], [], [], errors
    except Exception as exc:
        errors.append(f"خطأ في قراءة Excel: {exc}")
        return [], [], [], errors


def _read_csv_rows(file_path: Path) -> tuple[list[str], list[list], list[str], list[str]]:
    errors: list[str] = []
    try:
        text = file_path.read_text(encoding="utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        all_rows = list(reader)
        if not all_rows:
            errors.append("ملف CSV فارغ.")
            return [], [], ["CSV"], errors
        raw_headers = all_rows[0]
        data_rows = all_rows[1:]
        return raw_headers, data_rows, ["CSV"], errors
    except Exception as exc:
        errors.append(f"خطأ في قراءة CSV: {exc}")
        return [], [], [], errors


# ── Row → dict normalization ──────────────────────────────────────────────────

def _rows_to_dicts(data_rows: list[list], normalized_columns: list[str],
                   raw_headers: list[str]) -> list[dict]:
    """
    Map each raw data row to a dict of {canonical_col: raw_value}.
    raw_headers and normalized_columns must be index-aligned with
    detect_columns output — we map only the columns that were successfully
    normalized.
    """
    # Build index: raw_header_index → canonical_name
    # (only for headers that were in the detected set)
    col_index: dict[int, str] = {}
    # We need the original-header-position mapping
    # normalize_columns returns detected (subset of raw) and normalized (canonical)
    # We need to rebuild a full-width mapping.
    # For simplicity, iterate raw_headers and normalize each one.
    from tax_appeal_structured_parser import _ALIAS_MAP  # self-import safe
    # We don't know evidence type here — caller must pass normalized mapping.
    # This function receives normalized_columns already paired with raw_headers
    # at the DETECTED positions.  We'll just use position matching:
    #   raw_headers[i]  -> if it normalized to something, use that canonical name
    # For now, use the columns that were successfully detected.
    # Since normalize_columns already de-duped, we just iterate all raw headers
    # and normalize again via the caller-provided evidence_type.
    # We'll re-do normalization inline:
    result_dicts: list[dict] = []
    for raw_row in data_rows:
        row_dict: dict = {}
        for i, raw_val in enumerate(raw_row):
            if i < len(normalized_columns):
                col_name = normalized_columns[i]
                if col_name:
                    row_dict[col_name] = raw_val
        result_dicts.append(row_dict)
    return result_dicts


def _map_rows(data_rows: list[list], raw_headers: list[str],
              evidence_type: str) -> tuple[list[dict], list[dict], list[str]]:
    """
    Map data rows to canonical-column dicts for a specific evidence type.

    Returns (usable_rows, rejected_rows, warnings)
    """
    warnings_out: list[str] = []
    aliases = _ALIAS_MAP.get(evidence_type, {})

    # Build per-column mapping: index → canonical_name (or None)
    col_map: list[Optional[str]] = []
    seen: set[str] = set()
    for header in raw_headers:
        canonical = _normalize_col(header, aliases)
        if canonical and canonical not in seen:
            col_map.append(canonical)
            seen.add(canonical)
        else:
            col_map.append(None)

    # Check required columns
    required = _REQUIRED_COLUMNS.get(evidence_type, [])
    present_canonicals = {c for c in col_map if c}
    for req in required:
        if req not in present_canonicals:
            warnings_out.append(f"عمود مطلوب مفقود: '{req}'")

    # Map rows
    all_dicts: list[dict] = []
    for raw_row in data_rows:
        row_dict: dict = {}
        for i, val in enumerate(raw_row):
            if i < len(col_map) and col_map[i]:
                row_dict[col_map[i]] = val
        all_dicts.append(row_dict)

    # Split usable / rejected
    numeric_keys = {
        "area_m2", "sale_price", "price_per_m2", "adjustment_percent",
        "adjusted_price_per_m2", "monthly_rent", "annual_rent", "rent_per_m2",
        "adjusted_rent_per_m2", "annual_tax", "tax_per_m2", "adjusted_tax_per_m2",
    }
    usable: list[dict] = []
    rejected: list[dict] = []
    for row_dict in all_dicts:
        has_numeric = any(
            _parse_float(row_dict.get(c)) is not None
            for c in present_canonicals
            if c in numeric_keys
        )
        if has_numeric:
            usable.append(row_dict)
        else:
            rejected.append(row_dict)

    return usable, rejected, warnings_out


# ── Safe row preview ──────────────────────────────────────────────────────────

def _safe_preview(rows: list[dict], max_rows: int = 5) -> list[dict]:
    """Return first N rows as safe string-valued dicts (no raw internal values)."""
    preview: list[dict] = []
    for row in rows[:max_rows]:
        safe_row = {k: str(v)[:80] if v is not None else "" for k, v in row.items()}
        preview.append(safe_row)
    return preview


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_structured_comparables(
    file_path: str | Path,
    evidence_type: str,
    evidence_id: str = "",
    request_id: str = "",
) -> dict:
    """
    Parse a comparables Excel/CSV file for advisory candidate summaries.

    Always returns a safe dict.  Never raises.
    All safety invariants are enforced unconditionally.

    Args:
        file_path:     Path to the .xlsx / .xls / .csv file.
        evidence_type: Must be one of STRUCTURED_EVIDENCE_TYPES.
        evidence_id:   Opaque evidence record ID (used for tracing only).
        request_id:    Tax appeal request ID (used for tracing only).

    Returns:
        Full structured parse result dict.
    """
    parse_job_id = _new_parse_job_id()
    result = _base_result(parse_job_id, evidence_id, request_id, evidence_type)

    if evidence_type not in STRUCTURED_EVIDENCE_TYPES:
        result["errors"].append(
            f"نوع المستند '{evidence_type}' غير مدعوم بالمحلل الجدولي. "
            f"المدعومة: {sorted(STRUCTURED_EVIDENCE_TYPES)}"
        )
        return _enforce_invariants(result)

    path = Path(file_path)
    ext  = path.suffix.lower()

    if not path.exists():
        result["errors"].append("الملف غير موجود — لا يمكن قراءة المستند.")
        return _enforce_invariants(result)

    result["input_file_type"] = ext

    # ── Read raw rows ──────────────────────────────────────────────────────
    if ext in {".xlsx", ".xls"}:
        raw_headers, data_rows, sheet_names, read_errors = _read_excel_rows(path)
        result["parser_available"] = True
    elif ext == ".csv":
        raw_headers, data_rows, sheet_names, read_errors = _read_csv_rows(path)
        result["parser_available"] = True
    else:
        result["errors"].append(
            f"نوع الملف '{ext}' غير مدعوم. المدعومة: .xlsx, .xls, .csv"
        )
        return _enforce_invariants(result)

    result["sheet_names"] = sheet_names

    if read_errors:
        result["errors"].extend(read_errors)
        if not raw_headers:
            return _enforce_invariants(result)

    result["row_count"] = len(data_rows)

    # ── Normalize columns ──────────────────────────────────────────────────
    detected, normalized, unknown = normalize_columns(raw_headers, evidence_type)
    result["detected_columns"]   = detected
    result["normalized_columns"] = normalized

    if unknown:
        result["warnings"].append(
            f"أعمدة غير معروفة (تجاهَلت): {unknown}"
        )

    # ── Map rows ───────────────────────────────────────────────────────────
    usable_rows, rejected_rows, col_warnings = _map_rows(
        data_rows, raw_headers, evidence_type
    )
    result["warnings"].extend(col_warnings)
    result["usable_row_count"]  = len(usable_rows)
    result["rejected_row_count"] = len(rejected_rows)

    # ── Build candidate summary ────────────────────────────────────────────
    builder = _SUMMARY_BUILDERS.get(evidence_type)
    if builder and usable_rows:
        try:
            summary = builder(usable_rows, normalized)
            summary["source_quality_note"] = _source_quality_note(
                len(usable_rows), len(data_rows), col_warnings
            )
            result["candidate_summary"] = summary
        except Exception as exc:
            result["warnings"].append(f"خطأ في بناء ملخص المرشحين: {exc}")
    else:
        result["candidate_summary"] = {
            "comparable_count": 0,
            "usable_row_count": 0,
            "source_quality_note": _source_quality_note(0, len(data_rows), col_warnings),
        }

    # ── Safe row preview (expert only) ─────────────────────────────────────
    result["candidate_rows_preview"] = _safe_preview(usable_rows)

    return _enforce_invariants(result)


def parse_unsupported_evidence_type(evidence_type: str, evidence_id: str = "",
                                    request_id: str = "") -> dict:
    """Return a safe placeholder for a non-Excel evidence type."""
    result = _base_result(_new_parse_job_id(), evidence_id, request_id, evidence_type)
    result["errors"].append(
        f"نوع المستند '{evidence_type}' لا يدعم المحلل الجدولي. "
        "استخدم مسار OCR للمستندات النصية."
    )
    return _enforce_invariants(result)


def get_structured_parser_info() -> dict:
    """Return metadata about structured parser availability."""
    info: dict = {
        "parser_name":            "structured_parser_advisory",
        "supported_types":        sorted(STRUCTURED_EVIDENCE_TYPES),
        "advisory_label_ar":      ADVISORY_LABEL_AR,
        "openpyxl_available":     False,
        "openpyxl_version":       None,
        "csv_available":          True,
        "external_api_used":      False,
        "qdrant_used":            False,
        "rag_used":               False,
        "production_ready":       False,
        "certified_usage_allowed": False,
    }
    try:
        import openpyxl
        info["openpyxl_available"] = True
        info["openpyxl_version"]   = openpyxl.__version__
    except ImportError:
        pass
    return info
