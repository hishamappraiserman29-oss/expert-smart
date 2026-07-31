# -*- coding: utf-8 -*-
"""
tax_appeal_ocr_engine.py — Local OCR abstraction for Tax Appeal Evidence.

Strategy (priority order):
  1. TXT files      → direct text passthrough (no OCR needed)
  2. PDF files      → PyMuPDF text-layer extraction (local, offline)
  3. Image files    → pytesseract + Tesseract if available, else graceful fallback
  4. XLSX/XLS/CSV   → marked as structured extraction path (not OCR)
  5. Unsupported    → safe unsupported result

Rules (enforced always):
  - external_api_used = False
  - qdrant_used       = False
  - rag_used          = False
  - production_ready  = False   (OCR output always requires expert review)
  - No internal file paths in returned dicts
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────────────────

_SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
_SUPPORTED_PDF_EXTS   = {".pdf"}
_SUPPORTED_TXT_EXTS   = {".txt"}
_STRUCTURED_EXTS      = {".xlsx", ".xls", ".csv"}
_ALL_SUPPORTED        = _SUPPORTED_IMAGE_EXTS | _SUPPORTED_PDF_EXTS | _SUPPORTED_TXT_EXTS | _STRUCTURED_EXTS

_PREVIEW_CHARS = 1000   # raw_text_preview length cap

# ── ID generator ──────────────────────────────────────────────────────────────

def _new_job_id() -> str:
    return "OCR-" + uuid.uuid4().hex[:8].upper()


# ── Safe result builder ───────────────────────────────────────────────────────

def _base_result(job_id: str, engine_name: str, mime_type: str, languages: list[str]) -> dict:
    return {
        "ocr_job_id":           job_id,
        "engine_name":          engine_name,
        "engine_available":     False,
        "engine_version":       None,
        "input_mime_type":      mime_type,
        "page_count":           0,
        "languages_requested":  languages,
        "languages_used":       [],
        "text":                 "",
        "pages":                [],
        "confidence_overall":   0.0,
        "warnings":             [],
        "errors":               [],
        "raw_text_available":   False,
        "production_ready":     False,
        "external_api_used":    False,
        "qdrant_used":          False,
        "rag_used":             False,
    }


# ── Text passthrough (TXT) ────────────────────────────────────────────────────

def _run_txt_passthrough(file_path: Path, mime_type: str, languages: list[str]) -> dict:
    job_id = _new_job_id()
    result = _base_result(job_id, "txt_passthrough", mime_type, languages)
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        result.update({
            "engine_available":  True,
            "engine_version":    "passthrough-1.0",
            "page_count":        1,
            "languages_used":    ["auto"],
            "text":              text,
            "pages":             [{"page_number": 1, "text": text, "confidence": 1.0}],
            "confidence_overall": 1.0,
            "raw_text_available": True,
        })
    except Exception as exc:
        result["errors"].append(f"خطأ في قراءة ملف النص: {exc}")
    return result


# ── PDF text extraction via PyMuPDF ──────────────────────────────────────────

def _run_pdf_extraction(file_path: Path, mime_type: str, languages: list[str]) -> dict:
    job_id = _new_job_id()
    result = _base_result(job_id, "pymupdf_text_extraction", mime_type, languages)
    try:
        import fitz  # PyMuPDF
        result["engine_version"] = fitz.version[0]
        result["engine_available"] = True
        doc = fitz.open(str(file_path))
        pages_data: list[dict] = []
        all_text_parts: list[str] = []
        for i, page in enumerate(doc):
            text = page.get_text("text")
            pages_data.append({
                "page_number": i + 1,
                "text":        text,
                "confidence":  1.0 if text.strip() else 0.0,
            })
            all_text_parts.append(text)
        doc.close()
        full_text = "\n".join(all_text_parts)
        has_text = bool(full_text.strip())
        result.update({
            "page_count":         len(pages_data),
            "languages_used":     ["auto"],
            "text":               full_text,
            "pages":              pages_data,
            "confidence_overall": 1.0 if has_text else 0.0,
            "raw_text_available": has_text,
        })
        if not has_text:
            result["warnings"].append(
                "لا توجد طبقة نص قابلة للاستخراج في هذا الـ PDF. قد يكون مسحًا ضوئيًا بدون OCR مدمج."
            )
    except ImportError:
        result["errors"].append("مكتبة PyMuPDF غير متاحة في هذه البيئة.")
        result["engine_available"] = False
    except Exception as exc:
        result["errors"].append(f"خطأ في استخراج نص PDF: {exc}")
    return result


# ── Image OCR via pytesseract ──────────────────────────────────────────────────

def _run_image_ocr(file_path: Path, mime_type: str, languages: list[str]) -> dict:
    job_id = _new_job_id()
    result = _base_result(job_id, "tesseract_ocr", mime_type, languages)
    # Determine Tesseract language string
    tess_langs = "+".join(languages) if languages else "ara+eng"
    try:
        import pytesseract
        from PIL import Image
        result["engine_version"] = pytesseract.get_tesseract_version().vstring
        result["engine_available"] = True
        img = Image.open(str(file_path))
        try:
            raw_text = pytesseract.image_to_string(img, lang=tess_langs)
            used_langs = languages if languages else ["ara", "eng"]
        except pytesseract.TesseractError:
            # Fallback: try without specific language
            raw_text = pytesseract.image_to_string(img)
            used_langs = ["auto"]
            result["warnings"].append(
                f"لغة OCR '{tess_langs}' غير متاحة. جرى التراجع إلى اللغة التلقائية."
            )
        result.update({
            "page_count":         1,
            "languages_used":     used_langs,
            "text":               raw_text,
            "pages":              [{"page_number": 1, "text": raw_text, "confidence": 0.7}],
            "confidence_overall": 0.7,
            "raw_text_available": bool(raw_text.strip()),
        })
        if not raw_text.strip():
            result["warnings"].append("لم يُستخرج أي نص من الصورة. تحقق من جودة الصورة.")
    except ImportError:
        result["engine_available"] = False
        result["warnings"].append(
            "محرك OCR المحلي (pytesseract / Tesseract) غير متاح في هذه البيئة. "
            "سيتطلب الاستخراج الإدخال اليدوي من الخبير."
        )
    except Exception as exc:
        result["errors"].append(f"خطأ في تشغيل OCR على الصورة: {exc}")
    return result


# ── Structured file (XLSX etc.) ────────────────────────────────────────────────

def _run_structured_passthrough(file_path: Path, mime_type: str, languages: list[str]) -> dict:
    job_id = _new_job_id()
    result = _base_result(job_id, "structured_extraction_future", mime_type, languages)
    result["warnings"].append(
        "هذا النوع من الملفات (Excel/CSV) ليس ملف OCR. "
        "مسار الاستخراج المستقبلي: محلل بنيوي — غير مفعَّل حاليًا."
    )
    return result


# ── Unsupported ────────────────────────────────────────────────────────────────

def _run_unsupported(file_path: Path, mime_type: str, languages: list[str]) -> dict:
    job_id = _new_job_id()
    result = _base_result(job_id, "unsupported", mime_type, languages)
    result["errors"].append(
        f"نوع الملف غير مدعوم لـ OCR: {mime_type} / {file_path.suffix}"
    )
    return result


# ── Public API ─────────────────────────────────────────────────────────────────

def run_local_ocr(
    file_path: str | Path,
    mime_type: str,
    languages: Optional[list[str]] = None,
    mode: Optional[str] = None,
) -> dict:
    """
    Run local OCR on the given file.

    Always returns a safe dict with:
      external_api_used = False
      qdrant_used       = False
      rag_used          = False
      production_ready  = False

    Never raises; errors are reported inside result["errors"].
    """
    if languages is None:
        languages = ["ara", "eng"]

    path = Path(file_path)
    ext  = path.suffix.lower()

    if ext in _SUPPORTED_TXT_EXTS:
        result = _run_txt_passthrough(path, mime_type, languages)
    elif ext in _SUPPORTED_PDF_EXTS:
        result = _run_pdf_extraction(path, mime_type, languages)
    elif ext in _SUPPORTED_IMAGE_EXTS:
        result = _run_image_ocr(path, mime_type, languages)
    elif ext in _STRUCTURED_EXTS:
        result = _run_structured_passthrough(path, mime_type, languages)
    else:
        result = _run_unsupported(path, mime_type, languages)

    # Enforce invariants — cannot be overridden by any sub-routine
    result["external_api_used"] = False
    result["qdrant_used"]       = False
    result["rag_used"]          = False
    result["production_ready"]  = False

    # Add raw_text_preview (capped, expert-only — do not expose to ordinary users)
    text = result.get("text", "")
    result["raw_text_preview"] = text[:_PREVIEW_CHARS] if text else ""

    return result


def get_engine_info() -> dict:
    """Return metadata about available local OCR engines without touching files."""
    info: dict = {
        "pymupdf_available":     False,
        "pymupdf_version":       None,
        "tesseract_available":   False,
        "tesseract_version":     None,
        "pillow_available":      False,
        "pillow_version":        None,
        "external_api_used":     False,
        "qdrant_used":           False,
        "rag_used":              False,
        "pdf_text_extraction":   False,
        "image_ocr":             False,
        "txt_passthrough":       True,
        "structured_path":       False,
    }
    try:
        import fitz
        info["pymupdf_available"]   = True
        info["pymupdf_version"]     = fitz.version[0]
        info["pdf_text_extraction"] = True
    except ImportError:
        pass
    try:
        import pytesseract
        info["tesseract_version"]  = pytesseract.get_tesseract_version().vstring
        info["tesseract_available"] = True
        info["image_ocr"]           = True
    except Exception:
        pass
    try:
        import PIL
        info["pillow_available"] = True
        info["pillow_version"]   = PIL.__version__
    except ImportError:
        pass
    return info
