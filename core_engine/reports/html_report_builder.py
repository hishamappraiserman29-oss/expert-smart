"""html_report_builder.py — Produce self-contained HTML reports for all three valuation tiers.

Uses the same Jinja2 templates and enrichment pipeline as the PDF builder so that
HTML and PDF artifacts always derive from the same shared report context.

Security: autoescape=True is enabled so that all dynamic values inserted via
{{ }} expressions are HTML-escaped.  CSS and font data-URIs are explicitly
marked Markup (trusted) to prevent double-escaping.
"""
from __future__ import annotations

import pathlib
from typing import Any

_HERE = pathlib.Path(__file__).parent
_TEMPLATES = _HERE.parent / "templates" / "pdf"
_CSS_PATH = _TEMPLATES / "pv_design_system.css"

_REPORT_TYPES = ("traditional_report", "detailed_report", "professional_report")


def _load_font_css() -> str:
    try:
        import sys as _sys
        _sys.path.insert(0, str(_HERE.parent))
        from pdf_renderer import cairo_font_css  # type: ignore
        return cairo_font_css()
    except Exception:
        return ""


def _render_safe(enriched: dict, template_name: str, fmt_fn: Any, na_fn: Any, na_str: str) -> str:
    """Render a report template with autoescape=True for XSS prevention.

    css and font_css are marked as Markup (trusted own content) so they are
    not double-escaped.  All dynamic data values from *enriched* are HTML-escaped
    by the template engine — including user-supplied fields like location, property_type.
    """
    try:
        from jinja2 import Environment, FileSystemLoader
        from markupsafe import Markup
    except ImportError as exc:
        raise RuntimeError("Jinja2 and MarkupSafe are required: pip install jinja2 markupsafe") from exc

    css_str = _CSS_PATH.read_text(encoding="utf-8") if _CSS_PATH.exists() else ""
    font_css_str = _load_font_css()

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES)),
        autoescape=True,
    )
    env.globals["_fmt"] = fmt_fn
    env.globals["_na"] = na_fn

    tmpl = env.get_template(template_name)
    return tmpl.render(
        data=enriched,
        css=Markup(css_str),
        font_css=Markup(font_css_str),
        NA=Markup(na_str),
    )


def build_traditional_html_safe(data: dict) -> str:
    """Build Traditional tier HTML string with HTML-escaped user inputs."""
    try:
        from reports.pv_three_tier_pdf_builder import _enrich_traditional_data, _fmt, _na, _NA
    except ImportError:
        from core_engine.reports.pv_three_tier_pdf_builder import _enrich_traditional_data, _fmt, _na, _NA  # type: ignore
    enriched = _enrich_traditional_data(data)
    return _render_safe(enriched, "pv_traditional_report.html", _fmt, _na, _NA)


def build_detailed_html_safe(data: dict) -> str:
    """Build Detailed tier HTML string with HTML-escaped user inputs."""
    try:
        from reports.pv_three_tier_pdf_builder import _enrich_detailed_data, _fmt, _na, _NA
    except ImportError:
        from core_engine.reports.pv_three_tier_pdf_builder import _enrich_detailed_data, _fmt, _na, _NA  # type: ignore
    enriched = _enrich_detailed_data(data)
    return _render_safe(enriched, "pv_detailed_report.html", _fmt, _na, _NA)


def build_professional_html_safe(data: dict) -> str:
    """Build Professional tier HTML string with HTML-escaped user inputs."""
    try:
        from reports.pv_three_tier_pdf_builder import _enrich_professional_data, _fmt, _na, _NA
    except ImportError:
        from core_engine.reports.pv_three_tier_pdf_builder import _enrich_professional_data, _fmt, _na, _NA  # type: ignore
    enriched = _enrich_professional_data(data)
    return _render_safe(enriched, "pv_professional_report.html", _fmt, _na, _NA)


_BUILDERS = {
    "traditional_report": build_traditional_html_safe,
    "detailed_report": build_detailed_html_safe,
    "professional_report": build_professional_html_safe,
}

_TEMPLATE_NAMES = {
    "traditional_report": "pv_traditional_report.html",
    "detailed_report": "pv_detailed_report.html",
    "professional_report": "pv_professional_report.html",
}


def _safe_filename(name: str) -> str:
    """Return *name* with path separators and dangerous chars removed."""
    import re
    name = pathlib.Path(name).name
    name = re.sub(r"[^A-Za-z0-9_\-\.]+", "_", name)
    return name[:200] if name else "report.html"


def generate_html_report(
    data: dict,
    report_type: str,
    output_path: "str | pathlib.Path",
) -> pathlib.Path:
    """Build and save a self-contained HTML report to *output_path*.

    Uses the same enrichment pipeline as render_*_pdf() so PDF and HTML
    always derive from the same shared report snapshot.

    Parameters
    ----------
    data:
        Flat valuation dict (same payload passed to the PDF renderers).
    report_type:
        One of 'traditional_report', 'detailed_report', 'professional_report'.
    output_path:
        Absolute or relative path where the .html file should be written.

    Returns
    -------
    pathlib.Path
        The resolved output path on success.

    Raises
    ------
    ValueError
        If *report_type* is not one of the three valid values.
    RuntimeError
        If Jinja2 / MarkupSafe are unavailable.
    """
    if report_type not in _BUILDERS:
        raise ValueError(
            f"Unknown report_type {report_type!r}. Valid: {list(_BUILDERS.keys())}"
        )

    builder = _BUILDERS[report_type]
    html_str = builder(data)

    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_str, encoding="utf-8")
    return output_path
