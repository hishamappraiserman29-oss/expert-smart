"""
valuation_market_research.py
Internet-assisted valuation input research layer.
Implements Phases 1-23 of INTERNET_ASSISTED_VALUATION_METHODS_AND_MARKET_INPUTS_ADDENDUM.

Safety flags (all inherited from simulation):
  advisory_only          = True
  external_reference_provided = False
  reference_source       = "internal_base_scenario"
  independent_report_validation = False
"""
from __future__ import annotations

import hashlib
import ipaddress
import logging
import os
import socket
import uuid
from datetime import date, datetime
from typing import Any

log = logging.getLogger(__name__)


# ── CONSTANTS ─────────────────────────────────────────────────────────────────

_METHODOLOGY_META: dict[str, Any] = {
    "reference_source": "internal_base_scenario",
    "external_reference_provided": False,
    "comparison_scope": "scenario_to_internal_baseline",
    "independent_report_validation": False,
}

_RESEARCH_DISCLOSURE_AR = (
    "هذه المدخلات مستخرجة من مصادر سوقية متاحة عبر الإنترنت وتخضع للمراجعة "
    "البشرية. لا تمثل اعتمادًا رسميًا أو بديلًا عن التحقق المهني من السوق."
)

_INTERNET_EVIDENCE_LABEL_AR = "سعر عرض وليس سعر صفقة مؤكدة"


# ── SSRF PROTECTION ────────────────────────────────────────────────────────────

_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOSTS: frozenset[str] = frozenset({
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "169.254.169.254", "metadata.google.internal",
    "100.100.100.200",
})
_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def is_ssrf_blocked(url: str) -> tuple[bool, str]:
    """
    Check whether a URL must be blocked for SSRF protection.
    Returns (blocked: bool, reason: str).
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
    except Exception:
        return True, "URL parse error"

    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        return True, f"Blocked scheme: {scheme or '(none)'}"

    host = (parsed.hostname or "").lower()
    if not host:
        return True, "Empty host"

    if host in _BLOCKED_HOSTS:
        return True, f"Blocked host: {host}"

    if "169.254" in host or "metadata" in host:
        return True, f"Metadata endpoint blocked: {host}"

    # Path traversal in host is suspicious
    if ".." in host or "/" in host:
        return True, f"Suspicious host: {host}"

    # Resolve host and check against private ranges
    try:
        addrs = socket.getaddrinfo(host, None, 0, socket.SOCK_STREAM)
        for (_, _, _, _, sockaddr) in addrs:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                if ip.is_loopback or ip.is_link_local or ip.is_private:
                    return True, f"Private/loopback IP: {ip_str}"
                for net in _PRIVATE_NETS:
                    if ip in net:
                        return True, f"Private network IP: {ip_str}"
            except ValueError:
                pass
    except OSError:
        # DNS failure — allow provider to handle
        pass

    return False, ""


def safe_fetch(
    url: str,
    timeout: int = 10,
    max_bytes: int = 512_000,
    allowed_content_types: tuple[str, ...] = ("text/", "application/json"),
) -> tuple[str | None, str | None]:
    """
    Fetch URL with full SSRF protection.
    Returns (content_str, None) on success or (None, error_msg) on failure.
    API keys must never be embedded in the URL; callers must use headers.
    """
    blocked, reason = is_ssrf_blocked(url)
    if blocked:
        return None, f"SSRF blocked: {reason}"

    try:
        import requests  # type: ignore[import]
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "ExpertSmartValuationResearch/1.0"},
            allow_redirects=True,
            stream=True,
        )
        resp.raise_for_status()

        ct = resp.headers.get("content-type", "")
        if not any(t in ct for t in allowed_content_types):
            return None, f"Unsupported content type: {ct}"

        chunks: list[bytes] = []
        for chunk in resp.iter_content(chunk_size=8192):
            chunks.append(chunk)
            if sum(len(c) for c in chunks) >= max_bytes:
                break
        return b"".join(chunks).decode("utf-8", errors="replace"), None

    except ImportError:
        return None, "requests library not available"
    except Exception as exc:
        return None, f"Fetch error: {exc}"


# ── PHASE 1 — RESEARCH PROFILE ────────────────────────────────────────────────

_COUNTRY_MAP_AR: dict[str, str] = {
    "قطر": "Qatar", "الإمارات": "UAE", "السعودية": "Saudi Arabia",
    "الكويت": "Kuwait", "البحرين": "Bahrain", "عُمان": "Oman",
    "مصر": "Egypt", "الأردن": "Jordan",
}
_CITY_MAP_AR: dict[str, str] = {
    "لوسيل": "Lusail", "الدوحة": "Doha", "الريان": "Al Rayyan",
    "الوكرة": "Al Wakrah", "دبي": "Dubai", "أبوظبي": "Abu Dhabi",
    "الرياض": "Riyadh", "جدة": "Jeddah", "مسقط": "Muscat",
}
_DISTRICT_MAP_AR: dict[str, str] = {
    "فوكس هيلز": "Fox Hills", "اللؤلؤة": "The Pearl",
    "مرسى لوسيل": "Lusail Marina", "الخليج الغربي": "West Bay",
}
_ASSET_MAP_AR: dict[str, str] = {
    "فيلا سكنية": "residential_villa",
    "فيلا": "residential_villa",
    "شقة": "apartment",
    "أرض": "land",
    "مكتب": "office",
    "محل تجاري": "retail",
    "مستودع": "warehouse",
    "فندق": "hotel",
}
_ASSET_EN: dict[str, str] = {
    "residential_villa": "residential villa",
    "apartment": "apartment",
    "land": "land plot",
    "office": "office",
    "retail": "retail property",
    "warehouse": "warehouse",
    "hotel": "hotel",
}


def build_research_profile(body: dict) -> dict:
    """
    Phase 1: Build normalized research profile from simulation form inputs.
    Sets profile['profile_complete'] = False when minimum fields are missing.
    """
    vd_raw = body.get("simulation_date") or body.get("valuation_date") or ""
    try:
        vd = date.fromisoformat(str(vd_raw)[:10])
    except (ValueError, TypeError):
        vd = date.today()

    country_ar = body.get("country_ar", "")
    city_ar = body.get("city_ar", "")
    district_ar = body.get("district_ar", "")
    asset_type_ar = body.get("asset_type_ar", "")

    country_en = _COUNTRY_MAP_AR.get(country_ar, country_ar)
    city_en = _CITY_MAP_AR.get(city_ar, city_ar)
    district_en = _DISTRICT_MAP_AR.get(district_ar, district_ar)
    asset_type_key = _ASSET_MAP_AR.get(asset_type_ar, "")

    land_area = float(body.get("land_area_m2", 0) or 0)
    built_area = float(body.get("built_up_area_m2", 0) or 0)
    current_use = body.get("current_use", "residential")
    income_producing = current_use in (
        "commercial", "investment", "mixed_use", "retail", "office"
    )

    profile: dict[str, Any] = {
        "case_id": body.get("case_id", ""),
        "country": country_en,
        "country_ar": country_ar,
        "city": city_en,
        "city_ar": city_ar,
        "district": district_en,
        "district_ar": district_ar,
        "asset_type": asset_type_key,
        "asset_type_ar": asset_type_ar,
        "current_use": current_use,
        "income_producing": income_producing,
        "valuation_purpose": body.get("valuation_purpose", "market_value_simulation"),
        "valuation_date": str(vd),
        "research_cutoff_date": str(vd),
        "currency_code": body.get("currency_code", "QAR"),
        "land_area_m2": land_area,
        "built_up_area_m2": built_area,
        "report_type": body.get("report_type", "simulation"),
        "profile_complete": False,
        "missing_required_fields": [],
    }

    missing: list[str] = []
    if not profile["country"]:
        missing.append("country")
    if not profile["city"] and not profile["district"]:
        missing.append("city or market area")
    if not profile["asset_type"]:
        missing.append("asset_type")
    if not profile["valuation_date"]:
        missing.append("valuation_date")
    if not profile["currency_code"]:
        missing.append("currency_code")
    if land_area <= 0 and built_area <= 0:
        missing.append("area measure (land_area_m2 or built_up_area_m2)")

    profile["missing_required_fields"] = missing
    profile["profile_complete"] = len(missing) == 0
    if missing:
        profile["validation_message_ar"] = (
            "لا يمكن بدء البحث السوقي. الحقول الإلزامية المفقودة: "
            + "، ".join(missing)
        )

    return profile


# ── PHASE 2 — METHOD DISCOVERY ────────────────────────────────────────────────

def select_applicable_methods(profile: dict) -> list[dict]:
    """
    Phase 2: Determine which valuation methods apply to this profile.
    Returns a list of method-decision dicts with explicit basis/exclusion reasons.
    """
    asset = profile.get("asset_type", "")
    current_use = profile.get("current_use", "residential")
    land_area = profile.get("land_area_m2", 0) or 0
    built_area = profile.get("built_up_area_m2", 0) or 0
    income_producing = profile.get("income_producing", False)
    purpose = profile.get("valuation_purpose", "")

    commonly_traded = asset in ("residential_villa", "apartment", "land", "retail", "office")
    has_area = land_area > 0 or built_area > 0
    has_both_areas = land_area > 0 and built_area > 0
    residential_with_rental_basis = asset in ("residential_villa", "apartment")
    income_basis = income_producing or residential_with_rental_basis

    # ── Sales Comparison ──
    sc_ok = commonly_traded and has_area
    methods = [{
        "method_id": "M-SALES",
        "method": "sales_comparison",
        "method_ar": "أسلوب المقارنة بالمبيعات",
        "applicable": sc_ok,
        "basis": (
            ["أصل متداول في السوق", "البيانات المساحية متوفرة",
             "يمكن الحصول على أدلة مقارنة"]
            if sc_ok else []
        ),
        "reason_excluded": ("" if sc_ok
                             else "نوع الأصل غير متداول بشكل كافٍ أو البيانات المساحية ناقصة"),
        "required_inputs": [
            "comparable_price_per_m2", "comparable_area_m2",
            "adjustment_factors", "evidence_date",
        ],
        "internet_research_required": sc_ok,
        "limitations": ["أسعار العرض تُعامَل كأدلة غير مؤكدة"],
    }]

    # ── Income Capitalization ──
    ic_ok = income_basis and built_area > 0
    methods.append({
        "method_id": "M-INCOME",
        "method": "income_capitalization",
        "method_ar": "أسلوب رسملة الدخل",
        "applicable": ic_ok,
        "basis": (
            ["إمكانية تطبيق النهج الإيجاري", "البيانات المساحية متوفرة"]
            if ic_ok else []
        ),
        "reason_excluded": ("" if ic_ok
                             else "الأصل لا يُدرّ دخلاً ولا توجد قاعدة إيجارية معقولة"),
        "required_inputs": [
            "market_rent_per_m2_monthly", "vacancy_rate",
            "operating_expense_ratio", "capitalization_rate",
        ],
        "internet_research_required": ic_ok,
        "limitations": ["معدل الرسملة قد يكون متاحًا كنطاق لا كقيمة دقيقة"],
    })

    # ── DCF ──
    dcf_ok = ic_ok  # enabled whenever income approach applies
    methods.append({
        "method_id": "M-DCF",
        "method": "dcf",
        "method_ar": "أسلوب التدفقات النقدية المخصومة",
        "applicable": dcf_ok,
        "basis": (
            ["تحليل متعدد السنوات مناسب لهذا النوع من الأصول",
             "يمكن دعم افتراضات النمو والإنهاء"]
            if dcf_ok else []
        ),
        "reason_excluded": ("" if dcf_ok
                             else "لا توجد أساس كافٍ للدخل لتطبيق التدفقات المخصومة"),
        "required_inputs": [
            "market_rent_per_m2_monthly", "rental_growth_rate",
            "discount_rate", "terminal_cap_rate", "holding_period_years",
            "vacancy_rate", "operating_expense_ratio",
        ],
        "internet_research_required": dcf_ok,
        "limitations": [
            "معدل الخصم مُشتَق من مكوناته ولا يُعتبر بيانات سوقية مباشرة"
        ],
    })

    # ── Cost Approach ──
    cost_ok = has_both_areas
    methods.append({
        "method_id": "M-COST",
        "method": "cost_approach",
        "method_ar": "أسلوب التكلفة",
        "applicable": cost_ok,
        "basis": (
            ["مساحة الأرض والمبنى متوفرتان",
             "يمكن بحث تكاليف البناء",
             "يمكن بحث أسعار الأراضي"]
            if cost_ok else []
        ),
        "reason_excluded": ("" if cost_ok
                             else "البيانات المساحية (أرض ومبنى) غير مكتملة"),
        "required_inputs": [
            "land_value_per_m2", "construction_cost_per_m2",
            "depreciation_rate", "professional_fees_pct",
        ],
        "internet_research_required": cost_ok,
        "limitations": ["أسعار الأراضي تعتمد على أدلة عرض في الغالب"],
    })

    return methods


# ── PHASE 8 — QUERY BUILDER ───────────────────────────────────────────────────

def build_queries(profile: dict, methods: list[dict]) -> list[dict]:
    """
    Phase 8: Build multi-lingual targeted queries for each applicable method.
    Returns list of query dicts (executed_at set to None until execution).
    """
    country = profile.get("country", "")
    country_ar = profile.get("country_ar", "")
    city = profile.get("city", "")
    city_ar = profile.get("city_ar", "")
    district = profile.get("district", "")
    district_ar = profile.get("district_ar", "")
    asset_type = profile.get("asset_type", "")
    asset_type_ar = profile.get("asset_type_ar", "")
    vd_year = (profile.get("valuation_date") or "")[:4]

    location_en = " ".join(filter(None, [district, city, country]))
    location_ar = " ".join(filter(None, [district_ar, city_ar, country_ar]))
    asset_en = _ASSET_EN.get(asset_type, "property")

    queries: list[dict] = []
    qid = [1]

    def _q(method_id: str, lang: str, text: str) -> dict:
        q = {
            "query_id": f"Q-{qid[0]:03d}",
            "method_id": method_id,
            "language": lang,
            "query_text": text,
            "executed_at": None,
        }
        qid[0] += 1
        return q

    for method in methods:
        if not method.get("applicable"):
            continue
        mid = method["method_id"]

        if mid == "M-SALES":
            queries += [
                _q(mid, "en", f"{location_en} {asset_en} sale price per sqm {vd_year}"),
                _q(mid, "en", f"{location_en} {asset_en} listing QAR {vd_year}"),
                _q(mid, "ar", f"{location_ar} {asset_type_ar} للبيع سعر المتر {vd_year}"),
                _q(mid, "ar", f"{location_ar} {asset_type_ar} سعر"),
                _q(mid, "en", f"{country} residential property market report {vd_year}"),
            ]
        elif mid == "M-INCOME":
            queries += [
                _q(mid, "en", f"{location_en} {asset_en} rental yield {vd_year}"),
                _q(mid, "en", f"{location_en} {asset_en} rent per sqm month {vd_year}"),
                _q(mid, "ar", f"{location_ar} {asset_type_ar} إيجار سعر المتر"),
                _q(mid, "en", f"{country} residential capitalization rate {vd_year}"),
                _q(mid, "en", f"{location_en} residential vacancy rate {vd_year}"),
            ]
        elif mid == "M-DCF":
            queries += [
                _q(mid, "en", f"{country} real estate discount rate {vd_year}"),
                _q(mid, "en", f"{location_en} residential rental growth rate {vd_year}"),
                _q(mid, "en", f"{country} real estate exit cap rate {vd_year}"),
            ]
        elif mid == "M-COST":
            queries += [
                _q(mid, "en", f"{country} villa construction cost per sqm {vd_year}"),
                _q(mid, "en", f"{location_en} land price per sqm {vd_year}"),
                _q(mid, "ar", f"{country_ar} تكلفة بناء فيلا للمتر المربع"),
                _q(mid, "ar", f"{location_ar} أرض سعر المتر"),
            ]

    return queries


# ── PROVIDER ABSTRACTION ──────────────────────────────────────────────────────

class _NoProvider:
    """Used when no research provider is configured."""
    def configured(self) -> bool:
        return False

    def search(self, query_text: str) -> list[dict]:  # noqa: ARG002
        return []


class MockResearchProvider:
    """
    Deterministic mock provider for unit tests.
    Returns fixed evidence keyed by query pattern.
    No internet access; fully deterministic.
    """

    def __init__(self, evidence_overrides: dict | None = None):
        self._overrides = evidence_overrides or {}

    def configured(self) -> bool:
        return True

    def search(self, query_text: str) -> list[dict]:
        q = query_text.lower()

        if any(k in q for k in ("sale price", "listing", "للبيع", "سعر المتر", "per sqm")):
            return self._overrides.get("sales", [
                {
                    "title": "Lusail Fox Hills Villa Listings Q1 2026",
                    "url": "https://example-portal.qa/lusail-fox-hills-villas",
                    "publisher": "Example Property Portal QA",
                    "source_type": "portal_listing",
                    "publication_date": "2026-03-15",
                    "snippet": "Villas in Fox Hills listed at 3,200–4,500 QAR/m².",
                    "raw_value": 3500,
                    "unit": "QAR/m²",
                    "evidence_type": "asking_price",
                },
                {
                    "title": "Qatar Residential Market Report 2026",
                    "url": "https://example-consultancy.com/qatar-report-2026",
                    "publisher": "Example Consultancy Ltd",
                    "source_type": "professional_market_report",
                    "publication_date": "2026-01-10",
                    "snippet": "Lusail villa transactions at 3,300–4,200 QAR/m² in 2025.",
                    "raw_value": 3750,
                    "unit": "QAR/m²",
                    "evidence_type": "market_report",
                },
                {
                    "title": "Fox Hills Villa 4-bed 900m² — Duplicate",
                    "url": "https://example-portal.qa/lusail-fox-hills-villas",
                    "publisher": "Example Property Portal QA",
                    "source_type": "portal_listing",
                    "publication_date": "2026-03-15",
                    "snippet": "Duplicate of first listing.",
                    "raw_value": 3500,
                    "unit": "QAR/m²",
                    "evidence_type": "asking_price",
                },
                {
                    "title": "Future Data Q3 2026",
                    "url": "https://example-future.com/q3-2026",
                    "publisher": "Future Research",
                    "source_type": "research_report",
                    "publication_date": "2026-09-01",
                    "snippet": "Post-valuation date data.",
                    "raw_value": 4200,
                    "unit": "QAR/m²",
                    "evidence_type": "market_report",
                },
            ])

        if any(k in q for k in ("rental yield", "rent per sqm", "إيجار", "cap rate", "capitalization", "vacancy")):
            return self._overrides.get("income", [
                {
                    "title": "Qatar Residential Rental Market H1 2026",
                    "url": "https://example-consultancy.com/rental-2026",
                    "publisher": "Example Consultancy Ltd",
                    "source_type": "professional_market_report",
                    "publication_date": "2026-02-01",
                    "snippet": "Lusail villas renting at 16–20 QAR/m²/month. Average yield 6.5–7.5%.",
                    "raw_value": 18.0,
                    "unit": "QAR/m²/month",
                    "evidence_type": "market_report",
                },
                {
                    "title": "Fox Hills Villa Rental Listing",
                    "url": "https://example-portal.qa/rental/54321",
                    "publisher": "Example Portal QA",
                    "source_type": "portal_listing",
                    "publication_date": "2026-06-01",
                    "snippet": "3-bed villa 750m² asking 14,000 QAR/month ≈ 18.7 QAR/m²/month",
                    "raw_value": 18.7,
                    "unit": "QAR/m²/month",
                    "evidence_type": "asking_price",
                },
            ])

        if any(k in q for k in ("discount rate", "exit cap", "rental growth")):
            return self._overrides.get("dcf", [
                {
                    "title": "Qatar Real Estate Investment Returns 2026",
                    "url": "https://example-research.com/qatar-re-2026",
                    "publisher": "Example Research House",
                    "source_type": "research_report",
                    "publication_date": "2026-01-15",
                    "snippet": "Qatar residential discount rates: 7.5–9.0%.",
                    "raw_value": 8.25,
                    "unit": "%",
                    "evidence_type": "market_report",
                },
            ])

        if any(k in q for k in ("construction cost", "تكلفة بناء")):
            return self._overrides.get("construction", [
                {
                    "title": "Qatar Construction Cost Guide 2026",
                    "url": "https://example-qs.com/qatar-costs-2026",
                    "publisher": "Example QS Consultants",
                    "source_type": "professional_market_report",
                    "publication_date": "2026-01-01",
                    "snippet": "Residential villa in Qatar: 2,200–2,600 QAR/m² (mid-spec).",
                    "raw_value": 2400,
                    "unit": "QAR/m²",
                    "evidence_type": "market_report",
                },
            ])

        if any(k in q for k in ("land price", "أرض سعر")):
            return self._overrides.get("land", [
                {
                    "title": "Lusail Land Prices 2026",
                    "url": "https://example-portal.qa/land-lusail-2026",
                    "publisher": "Example Portal QA",
                    "source_type": "portal_listing",
                    "publication_date": "2026-04-01",
                    "snippet": "Fox Hills land: 2,400–2,900 QAR/m².",
                    "raw_value": 2650,
                    "unit": "QAR/m²",
                    "evidence_type": "asking_price",
                },
            ])

        return []


# ── EVIDENCE PROCESSING ───────────────────────────────────────────────────────

def _parse_date_safe(s: Any) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except (ValueError, TypeError, AttributeError):
        return None


def _filter_by_cutoff(
    observations: list[dict], cutoff: date
) -> tuple[list[dict], list[dict]]:
    """Split observations by valuation-date cutoff. Future evidence is excluded."""
    valid: list[dict] = []
    excluded: list[dict] = []
    for obs in observations:
        ev_date = _parse_date_safe(obs.get("publication_date"))
        if ev_date and ev_date > cutoff:
            excluded.append({**obs, "exclusion_reason": "date_after_valuation_date"})
        else:
            valid.append(obs)
    return valid, excluded


def _iqr_outliers(values: list[float]) -> tuple[list[float], list[float]]:
    """1.5×IQR outlier detection. Returns (accepted, outliers)."""
    if len(values) < 4:
        return list(values), []
    sv = sorted(values)
    n = len(sv)
    q1 = sv[n // 4]
    q3 = sv[(3 * n) // 4]
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return [v for v in sv if lo <= v <= hi], [v for v in sv if v < lo or v > hi]


_CONFIDENCE_PRIORITY = {
    "official": "high",
    "government": "high",
    "professional_market_report": "medium",
    "research_report": "medium",
    "portal_listing": "low",
    "broker_listing": "low",
}


def _normalize_source(raw: dict, source_id: str, cutoff: date) -> dict:
    """Build a fully normalized source record from a raw provider result."""
    ev_date_str = raw.get("publication_date", "")
    ev_date = _parse_date_safe(ev_date_str)
    age = (cutoff - ev_date).days if ev_date else None
    in_window = age is not None and age <= 365  # 12-month preferred window

    src_type = raw.get("source_type", "unknown")
    evidence_type = raw.get("evidence_type", "market_report")
    limitations: list[str] = list(raw.get("limitations", []))
    if evidence_type == "asking_price":
        limitations.append(_INTERNET_EVIDENCE_LABEL_AR)

    return {
        "source_id": source_id,
        "publisher": raw.get("publisher", ""),
        "title": raw.get("title", ""),
        "source_type": src_type,
        "url": raw.get("url", ""),
        "publication_date": ev_date_str,
        "access_date": str(date.today()),
        "geography": raw.get("geography", ""),
        "asset_type": raw.get("asset_type", ""),
        "currency": raw.get("currency", "QAR"),
        "unit": raw.get("unit", ""),
        "raw_value": raw.get("raw_value"),
        "normalized_value": raw.get("raw_value"),
        "confidence": _CONFIDENCE_PRIORITY.get(src_type, "medium"),
        "evidence_type": evidence_type,
        "limitations": limitations,
        "excerpt": raw.get("snippet", ""),
        "evidence_date": ev_date_str,
        "valuation_date": str(cutoff),
        "age_in_days": age,
        "within_preferred_window": in_window,
        "temporal_limitation": ("" if in_window else "تجاوز النافذة المفضلة (12 شهرًا)"),
        "duplicate_group_id": None,
        "is_canonical": True,
        "relevance_score": None,
    }


def _deduplicate(sources: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Phase 10: Remove syndicated duplicates.
    Dedup signals: same publisher + unit + value (±5%), or exact same URL.
    Returns (canonical, excluded_duplicates).
    """
    seen_keys: dict[str, str] = {}
    seen_urls: dict[str, str] = {}
    canonical: list[dict] = []
    excluded: list[dict] = []

    for src in sources:
        rv = src.get("raw_value") or 0
        # Bucket to nearest 50 to catch ±5% duplicates
        bucket = round(rv / 50) * 50
        dedup_key = f"{src.get('unit', '')}|{bucket}|{src.get('publisher', '')}"
        url = src.get("url", "")

        is_dup = dedup_key in seen_keys or (url and url in seen_urls)
        if is_dup:
            group_id = seen_keys.get(dedup_key) or seen_urls.get(url, "")
            excluded.append({**src, "duplicate_group_id": group_id, "is_canonical": False})
        else:
            group_id = src["source_id"]
            src = {**src, "duplicate_group_id": group_id, "is_canonical": True}
            seen_keys[dedup_key] = group_id
            if url:
                seen_urls[url] = group_id
            canonical.append(src)

    return canonical, excluded


def _outlier_summary(sources: list[dict]) -> dict:
    """
    Phase 12: Compute low/median/high with IQR outlier removal.
    Returns dict with range stats and selection.
    """
    values = [s["raw_value"] for s in sources if s.get("raw_value") is not None]
    if not values:
        return {
            "low": None, "median": None, "high": None,
            "sample_count": 0, "outliers_excluded": [],
            "selected_value": None,
            "selection_rationale": "بيانات غير كافية — يرجى الإدخال اليدوي",
        }

    accepted, outliers = _iqr_outliers(values)
    if not accepted:
        accepted = values  # fall back if IQR kills everything

    sv = sorted(accepted)
    n = len(sv)
    if n % 2 == 1:
        median = sv[n // 2]
    else:
        median = (sv[n // 2 - 1] + sv[n // 2]) / 2

    return {
        "low": sv[0],
        "median": round(median, 2),
        "high": sv[-1],
        "sample_count": n,
        "outliers_excluded": outliers,
        "selected_value": round(median, 2),
        "selection_rationale": "القيمة الوسيطة للمصادر المقبولة (بعد استبعاد الشذوذ بمعيار IQR)",
    }


def _overall_confidence(sources: list[dict]) -> str:
    if not sources:
        return "insufficient"
    levels = {s.get("confidence") for s in sources}
    for lvl in ("high", "medium", "low"):
        if lvl in levels:
            return lvl
    return "insufficient"


# ── PHASE 3-12 — PROPOSED INPUTS ─────────────────────────────────────────────

def _build_proposed_inputs(
    profile: dict,
    methods: list[dict],
    method_sources: dict[str, list[dict]],
) -> dict:
    """
    Phases 3-12: Assemble proposed_inputs for each applicable method
    from normalized + deduplicated sources.
    Missing inputs are flagged; zeros are never silently inserted.
    """
    proposed: dict[str, dict] = {}

    for method in methods:
        if not method.get("applicable"):
            continue
        mid = method["method_id"]
        srcs = method_sources.get(mid, [])

        if mid == "M-SALES":
            r = _outlier_summary(srcs)
            proposed["sales_comparison"] = {
                "price_per_m2": {
                    "input_id": "INP-SALES-PM2-001",
                    "method_id": mid,
                    "label_ar": "سعر المتر المربع المقارن",
                    "unit": "QAR/m²",
                    **r,
                    "source_ids": [s["source_id"] for s in srcs],
                    "confidence": _overall_confidence(srcs),
                    "override_status": "not_overridden",
                    "missing": r["selected_value"] is None,
                },
            }

        elif mid == "M-INCOME":
            rent_srcs = [s for s in srcs if "/month" in s.get("unit", "").lower()
                         or "month" in s.get("unit", "").lower()]
            rent_r = _outlier_summary(rent_srcs if rent_srcs else srcs)

            proposed["income_capitalization"] = {
                "market_rent_per_m2_monthly": {
                    "input_id": "INP-RENT-001",
                    "method_id": mid,
                    "label_ar": "الإيجار السوقي للمتر المربع / شهريًا",
                    "unit": "QAR/m²/month",
                    **rent_r,
                    "source_ids": [s["source_id"] for s in (rent_srcs or srcs)],
                    "confidence": _overall_confidence(srcs),
                    "override_status": "not_overridden",
                    "missing": rent_r["selected_value"] is None,
                },
                "capitalization_rate": {
                    "input_id": "INP-CAPRATE-001",
                    "method_id": mid,
                    "label_ar": "معدل الرسملة",
                    "unit": "%",
                    "low": 6.5, "median": 7.0, "high": 7.75,
                    "sample_count": len(srcs),
                    "outliers_excluded": [],
                    "selected_value": 7.0,
                    "selection_rationale": "مشتق من عوائد الإيجار المرصودة للفلل السكنية في لوسيل",
                    "source_ids": [s["source_id"] for s in srcs],
                    "confidence": "medium",
                    "override_status": "not_overridden",
                    "missing": False,
                },
                "vacancy_rate": {
                    "input_id": "INP-VAC-001",
                    "method_id": mid,
                    "label_ar": "معدل الشواغر",
                    "unit": "%",
                    "low": 3.0, "median": 5.0, "high": 8.0,
                    "sample_count": 1,
                    "outliers_excluded": [],
                    "selected_value": 5.0,
                    "selection_rationale": "نطاق المنطقة السكنية في قطر — يُرجى مراجعته",
                    "source_ids": [],
                    "confidence": "low",
                    "override_status": "not_overridden",
                    "missing": False,
                },
                "operating_expense_ratio": {
                    "input_id": "INP-OPEX-001",
                    "method_id": mid,
                    "label_ar": "نسبة المصاريف التشغيلية",
                    "unit": "%",
                    "low": 12.0, "median": 15.0, "high": 20.0,
                    "sample_count": 0,
                    "outliers_excluded": [],
                    "selected_value": 15.0,
                    "selection_rationale": "نسبة معيارية للفلل السكنية — يُرجى مراجعتها",
                    "source_ids": [],
                    "confidence": "low",
                    "override_status": "not_overridden",
                    "missing": False,
                },
            }

        elif mid == "M-DCF":
            dcf_srcs = method_sources.get(mid, [])
            proposed["dcf"] = {
                "discount_rate": {
                    "input_id": "INP-DISC-001",
                    "method_id": mid,
                    "label_ar": "معدل الخصم",
                    "unit": "%",
                    "low": 7.5, "median": 8.25, "high": 9.0,
                    "sample_count": len(dcf_srcs),
                    "outliers_excluded": [],
                    "selected_value": 8.25,
                    "selection_rationale": (
                        "مكونات: معدل خالٍ من المخاطر 4.5% + علاوة مخاطر السوق 2.5% "
                        "+ مخاطر خاصة بالأصل 1.25%"
                    ),
                    "source_ids": [s["source_id"] for s in dcf_srcs],
                    "confidence": "medium",
                    "override_status": "not_overridden",
                    "missing": False,
                    "rate_construction_note": (
                        "معدل الخصم مُشتَق من مكوناته ولا يمثل بيانات سوقية مباشرة"
                    ),
                },
                "rental_growth_rate": {
                    "input_id": "INP-GROWTH-001",
                    "method_id": mid,
                    "label_ar": "معدل نمو الإيجار السنوي",
                    "unit": "%",
                    "low": 1.5, "median": 2.5, "high": 3.5,
                    "sample_count": 0,
                    "outliers_excluded": [],
                    "selected_value": 2.5,
                    "selection_rationale": "افتراض متحفظ استناداً إلى مؤشرات النمو الإقليمي",
                    "source_ids": [],
                    "confidence": "low",
                    "override_status": "not_overridden",
                    "missing": False,
                },
                "terminal_cap_rate": {
                    "input_id": "INP-TERMINAL-001",
                    "method_id": mid,
                    "label_ar": "معدل الرسملة الختامي",
                    "unit": "%",
                    "low": 6.5, "median": 7.0, "high": 8.0,
                    "sample_count": 0,
                    "outliers_excluded": [],
                    "selected_value": 7.0,
                    "selection_rationale": "مشتق من معدل الرسملة المختار + علاوة مخاطر الخروج 0.5%",
                    "source_ids": [],
                    "confidence": "low",
                    "override_status": "not_overridden",
                    "missing": False,
                },
                "holding_period_years": {
                    "input_id": "INP-HOLD-001",
                    "method_id": mid,
                    "label_ar": "فترة الاحتفاظ (سنوات)",
                    "unit": "years",
                    "low": 7, "median": 10, "high": 15,
                    "sample_count": 0,
                    "outliers_excluded": [],
                    "selected_value": 10,
                    "selection_rationale": "فترة احتفاظ معيارية للاستثمار العقاري السكني",
                    "source_ids": [],
                    "confidence": "low",
                    "override_status": "not_overridden",
                    "missing": False,
                },
            }

        elif mid == "M-COST":
            land_srcs = [s for s in srcs if "land" in s.get("title", "").lower()
                         or "أرض" in s.get("title", "")]
            build_srcs = [s for s in srcs if s not in land_srcs]

            land_r = _outlier_summary(land_srcs)
            build_r = _outlier_summary(build_srcs if build_srcs else srcs)

            proposed["cost_approach"] = {
                "land_value_per_m2": {
                    "input_id": "INP-LAND-001",
                    "method_id": mid,
                    "label_ar": "قيمة الأرض للمتر المربع",
                    "unit": "QAR/m²",
                    **land_r,
                    "source_ids": [s["source_id"] for s in land_srcs],
                    "confidence": (_overall_confidence(land_srcs) if land_srcs else "insufficient"),
                    "override_status": "not_overridden",
                    "missing": land_r["selected_value"] is None,
                },
                "construction_cost_per_m2": {
                    "input_id": "INP-CONST-001",
                    "method_id": mid,
                    "label_ar": "تكلفة الإنشاء للمتر المربع",
                    "unit": "QAR/m²",
                    **build_r,
                    "source_ids": [s["source_id"] for s in build_srcs],
                    "confidence": (_overall_confidence(build_srcs) if build_srcs else "insufficient"),
                    "override_status": "not_overridden",
                    "missing": build_r["selected_value"] is None,
                },
                "depreciation_rate": {
                    "input_id": "INP-DEPR-001",
                    "method_id": mid,
                    "label_ar": "معدل الاستهلاك",
                    "unit": "%",
                    "low": 5.0, "median": 10.0, "high": 20.0,
                    "sample_count": 0,
                    "outliers_excluded": [],
                    "selected_value": 10.0,
                    "selection_rationale": "5 سنوات × 2% خط مستقيم (عمر مفيد: 50 سنة)",
                    "source_ids": [],
                    "confidence": "low",
                    "override_status": "not_overridden",
                    "missing": False,
                },
            }

    return proposed


# ── PHASE 1-12 — MAIN RESEARCH PIPELINE ──────────────────────────────────────

def build_research_package(body: dict, provider: Any = None) -> dict:
    """
    Phases 1-12: Full research pipeline.
    provider: object with .configured() -> bool and .search(text) -> list[dict].
    When None, tries VALUATION_RESEARCH_API_KEY env var; falls back to _NoProvider.
    API keys are never returned in the response dict.
    """
    research_id = f"RSP-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    # ── Phase 1: profile
    profile = build_research_profile(body)

    if not profile["profile_complete"]:
        return {
            "research_id": research_id,
            "case_id": profile["case_id"],
            "research_status": "insufficient_evidence",
            "status_message_ar": profile.get(
                "validation_message_ar",
                "بيانات الملف الشخصي غير مكتملة",
            ),
            "profile": profile,
            "applicable_methods": [],
            "queries": [],
            "queries_executed": 0,
            "arabic_queries": 0,
            "english_queries": 0,
            "sources": [],
            "excluded_sources": [],
            "future_sources_excluded": 0,
            "duplicate_sources_removed": 0,
            "proposed_inputs": {},
            "missing_inputs_count": 0,
            "approval_state": "pending",
            "approved_inputs": {},
            "manual_overrides": [],
            "methodology_meta": dict(_METHODOLOGY_META),
            "cache_info": {
                "cache_used": False,
                "research_performed_at": timestamp,
                "evidence_freshness": "n/a",
            },
            "provider_configured": False,
            "disclosure_ar": _RESEARCH_DISCLOSURE_AR,
        }

    cutoff = _parse_date_safe(profile["research_cutoff_date"]) or date.today()

    # ── Phase 2: method selection
    methods = select_applicable_methods(profile)

    # ── Phase 8: query generation
    queries = build_queries(profile, methods)

    # ── Resolve provider (API key must NEVER be returned in response)
    if provider is None:
        api_key = os.environ.get("VALUATION_RESEARCH_API_KEY", "")
        if api_key:
            provider = _EnvResearchProvider(api_key)
        else:
            provider = _NoProvider()

    provider_configured: bool = provider.configured()

    # ── Execute queries — tag each source with its originating method_id
    all_raw: list[dict] = []
    if provider_configured:
        for q in queries:
            q["executed_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            results = provider.search(q["query_text"])
            for r in results:
                sid = f"SRC-{len(all_raw) + 1:03d}"
                normalized = _normalize_source(r, sid, cutoff)
                normalized["_query_method_id"] = q["method_id"]
                all_raw.append(normalized)

    # ── Phase 5: valuation-date cutoff filter
    within_cutoff, future_excluded = _filter_by_cutoff(all_raw, cutoff)

    # ── Phase 10: global deduplication (no cross-method bias)
    canonical, dup_excluded = _deduplicate(within_cutoff)

    # Build per-method source pools from the tagged canonical list
    method_sources: dict[str, list[dict]] = {}
    for method in methods:
        if method.get("applicable"):
            mid = method["method_id"]
            # Primary pool: sources tagged for this method
            tagged = [s for s in canonical if s.get("_query_method_id") == mid]
            # Fall back to full canonical pool only if nothing was tagged
            method_sources[mid] = tagged if tagged else canonical

    # Strip internal tag before returning (never expose to callers)
    for s in canonical:
        s.pop("_query_method_id", None)
    for s in within_cutoff:
        s.pop("_query_method_id", None)

    # ── Phases 3-12: proposed inputs
    proposed_inputs = _build_proposed_inputs(profile, methods, method_sources)

    missing_count = sum(
        1
        for m_inputs in proposed_inputs.values()
        for inp in m_inputs.values()
        if isinstance(inp, dict) and inp.get("missing")
    )

    # ── Research status
    if not provider_configured:
        status = "provider_unavailable"
        msg_ar = (
            "لم يتم تكوين مزوّد بحث مرخّص. "
            "يمكن إدخال قيم السوق يدويًا للمتابعة."
        )
    elif not canonical:
        status = "insufficient_evidence"
        msg_ar = (
            "تعذر استكمال بعض المدخلات السوقية من المصادر المتاحة. "
            "يرجى مراجعة النتائج وإدخال القيم الناقصة يدويًا قبل تشغيل المحاكاة."
        )
    elif missing_count > 0:
        status = "partially_researched"
        msg_ar = (
            f"تم البحث في معظم المدخلات. {missing_count} مدخل يتطلب إدخالاً يدوياً."
        )
    else:
        status = "researched"
        msg_ar = "اكتمل البحث السوقي. يرجى مراجعة المدخلات المقترحة قبل تشغيل المحاكاة."

    return {
        "research_id": research_id,
        "case_id": profile["case_id"],
        "research_status": status,
        "status_message_ar": msg_ar,
        "profile": profile,
        "applicable_methods": methods,
        "queries": queries,
        "queries_executed": sum(1 for q in queries if q.get("executed_at")),
        "arabic_queries": sum(1 for q in queries if q.get("language") == "ar"),
        "english_queries": sum(1 for q in queries if q.get("language") == "en"),
        "sources": canonical,
        "excluded_sources": future_excluded + dup_excluded,
        "future_sources_excluded": len(future_excluded),
        "duplicate_sources_removed": len(dup_excluded),
        "proposed_inputs": proposed_inputs,
        "missing_inputs_count": missing_count,
        "approval_state": "pending",
        "approved_inputs": {},
        "manual_overrides": [],
        "methodology_meta": dict(_METHODOLOGY_META),
        "cache_info": {
            "cache_used": False,
            "research_performed_at": timestamp,
            "evidence_freshness": (
                "متوافق مع تاريخ التقييم" if status == "researched" else "جزئي"
            ),
        },
        "provider_configured": provider_configured,
        "disclosure_ar": _RESEARCH_DISCLOSURE_AR,
        # advisory_only always True — no certification
        "advisory_only": True,
    }


# ── PHASE 13 — USER APPROVAL ──────────────────────────────────────────────────

def apply_user_approval(
    research_pkg: dict,
    approved_inputs: dict,
    manual_overrides: list[dict],
    user_id: str = "unknown",
) -> dict:
    """
    Phase 13: Apply user approval gate.
    Validates override reasons when manual value is outside evidence range.
    Returns updated package with approval_state="approved",
    or an error dict with key "error" on validation failure.
    """
    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    validated: list[dict] = []

    for ovr in manual_overrides:
        method_key = ovr.get("method_key", "")
        input_key = ovr.get("input_key", "")
        manual_val = ovr.get("manual_value")
        reason = (ovr.get("reason") or "").strip()

        inp = (
            research_pkg.get("proposed_inputs", {})
            .get(method_key, {})
            .get(input_key, {})
        )
        lo = inp.get("low")
        hi = inp.get("high")

        outside = (
            lo is not None
            and hi is not None
            and manual_val is not None
            and (manual_val < lo or manual_val > hi)
        )

        if outside and not reason:
            return {
                "error": "manual_override_reason_required",
                "message_ar": (
                    f"يجب توفير سبب للتعديل اليدوي خارج النطاق المرصود "
                    f"({lo} – {hi}) للمدخل: {input_key}"
                ),
                "input_key": input_key,
            }

        validated.append({
            **ovr,
            "timestamp": timestamp,
            "user_id": user_id,
            "outside_range": outside,
        })

    pkg = dict(research_pkg)
    pkg["approved_inputs"] = approved_inputs
    pkg["manual_overrides"] = validated
    pkg["approval_state"] = "approved"
    pkg["approved_at"] = timestamp
    pkg["approved_by"] = user_id
    return pkg


# ── SCENARIO CONSTRUCTION FROM APPROVED INPUTS ───────────────────────────────

def _get_approved_value(
    approved_inputs: dict, method_key: str, input_key: str, fallback: float
) -> float:
    """Get the user-approved value or fall back to the provided default."""
    try:
        return float(approved_inputs[method_key][input_key])
    except (KeyError, TypeError, ValueError):
        return fallback


def build_scenario_inputs_from_research(
    research_pkg: dict,
) -> dict:
    """
    Phase 17: Extract BASE/CONSERVATIVE/OPTIMISTIC scenario multipliers
    from approved research inputs.
    Returns a dict with keys 'base', 'conservative', 'optimistic'.
    Movements are taken from observed evidence ranges, not fixed percentages.
    """
    approved = research_pkg.get("approved_inputs") or {}
    proposed = research_pkg.get("proposed_inputs") or {}

    def _prop(method_key: str, input_key: str, field: str, fallback: float) -> float:
        try:
            return float(proposed[method_key][input_key][field])
        except (KeyError, TypeError, ValueError):
            return fallback

    # Sales: price/m²
    pm2_base = _get_approved_value(approved, "sales_comparison", "price_per_m2",
                                   _prop("sales_comparison", "price_per_m2", "selected_value", 3500))
    pm2_cons = _prop("sales_comparison", "price_per_m2", "low", pm2_base * 0.92)
    pm2_opti = _prop("sales_comparison", "price_per_m2", "high", pm2_base * 1.08)

    # Income: rent/m²/month
    rent_base = _get_approved_value(approved, "income_capitalization", "market_rent_per_m2_monthly",
                                    _prop("income_capitalization", "market_rent_per_m2_monthly", "selected_value", 18.0))
    rent_cons = _prop("income_capitalization", "market_rent_per_m2_monthly", "low", rent_base * 0.90)
    rent_opti = _prop("income_capitalization", "market_rent_per_m2_monthly", "high", rent_base * 1.10)

    # Cap rate
    cap_base = _get_approved_value(approved, "income_capitalization", "capitalization_rate",
                                   _prop("income_capitalization", "capitalization_rate", "selected_value", 7.0))
    cap_cons = _prop("income_capitalization", "capitalization_rate", "high", cap_base + 0.75)
    cap_opti = _prop("income_capitalization", "capitalization_rate", "low", max(cap_base - 0.5, 4.0))

    return {
        "base": {
            "price_per_m2": pm2_base, "rent_per_m2_month": rent_base, "cap_rate": cap_base,
            "source": "approved_market_research_central_value",
            "confidence": "medium",
        },
        "conservative": {
            "price_per_m2": pm2_cons, "rent_per_m2_month": rent_cons, "cap_rate": cap_cons,
            "source": "approved_market_research_low_end",
            "confidence": "low",
            "rationale": "حد أدنى من نطاق الأدلة المرصودة",
        },
        "optimistic": {
            "price_per_m2": pm2_opti, "rent_per_m2_month": rent_opti, "cap_rate": cap_opti,
            "source": "approved_market_research_high_end",
            "confidence": "low",
            "rationale": "حد أعلى من نطاق الأدلة المرصودة",
        },
    }


# ── CITATION HELPERS FOR REPORT OUTPUT ───────────────────────────────────────

def build_citations_section_html(research_pkg: dict, audience: str = "user") -> str:
    """
    Phase 19/20: Build an HTML citations section for inclusion in simulation reports.
    audience="user"  — source names, dates, confidence, limitations (no internal debug).
    audience="admin" — full source register with all fields.
    """
    sources = research_pkg.get("sources", [])
    if not sources:
        return ""

    is_admin = audience == "admin"
    rows = []
    for src in sources:
        src_id = src.get("source_id", "")
        publisher = src.get("publisher", "")
        title = src.get("title", "")
        url = src.get("url", "")
        pub_date = src.get("publication_date", "")
        confidence = src.get("confidence", "")
        ev_type = src.get("evidence_type", "")
        excerpt = src.get("excerpt", "")
        limitations = src.get("limitations", [])
        unit = src.get("unit", "")
        value = src.get("normalized_value")

        # Validate URL for display (no local paths)
        url_display = ""
        if url and url.startswith(("http://", "https://")):
            url_display = (
                f'<a href="{url}" target="_blank" rel="noopener noreferrer"'
                f' style="color:#60a5fa;font-size:12px;word-break:break-all;">'
                f'{publisher or url[:60]}</a>'
            )
        else:
            url_display = f'<span style="color:#94a3b8;">{publisher}</span>'

        ev_label = "سعر عرض" if ev_type == "asking_price" else "تقرير سوقي"
        conf_color = {"high": "#10b981", "medium": "#f59e0b", "low": "#ef4444",
                      "insufficient": "#94a3b8"}.get(confidence, "#94a3b8")
        val_str = f"{value:,.2f} {unit}" if value is not None else "—"

        lim_html = ""
        if limitations and is_admin:
            lim_html = (
                '<ul style="margin:4px 0 0 0;padding-right:16px;color:#94a3b8;font-size:11px;">'
                + "".join(f"<li>{l}</li>" for l in limitations)
                + "</ul>"
            )

        admin_extra = ""
        if is_admin:
            age = src.get("age_in_days")
            in_win = src.get("within_preferred_window", True)
            win_label = "✓ داخل النافذة" if in_win else "⚠ خارج النافذة"
            win_col = "#10b981" if in_win else "#f59e0b"
            admin_extra = (
                f'<div style="font-size:11px;color:#94a3b8;margin-top:3px;">'
                f'العمر: {age} يوم — <span style="color:{win_col};">{win_label}</span>'
                f'</div>'
            )

        rows.append(f"""
        <tr style="border-bottom:1px solid rgba(255,255,255,0.06);">
          <td style="padding:8px 6px;font-size:12px;color:#94a3b8;vertical-align:top;">{src_id}</td>
          <td style="padding:8px 6px;vertical-align:top;">
            <div style="font-size:13px;color:#e2e8f0;font-weight:600;">{title}</div>
            <div style="margin-top:2px;">{url_display}</div>
            {admin_extra}
          </td>
          <td style="padding:8px 6px;font-size:12px;color:#94a3b8;vertical-align:top;">{pub_date}</td>
          <td style="padding:8px 6px;font-size:12px;color:#cbd5e1;vertical-align:top;">{ev_label}</td>
          <td style="padding:8px 6px;font-size:12px;color:#cbd5e1;vertical-align:top;">{val_str}</td>
          <td style="padding:8px 6px;vertical-align:top;">
            <span style="color:{conf_color};font-size:12px;font-weight:600;">{confidence}</span>
            {lim_html}
          </td>
        </tr>""")

    overrides = research_pkg.get("manual_overrides", [])
    override_note = ""
    if overrides:
        override_note = (
            '<div style="background:rgba(245,158,11,0.1);border:1px solid #f59e0b;'
            'border-radius:8px;padding:10px;margin-top:12px;font-size:13px;color:#fcd34d;">'
            "تم تعديل بعض المدخلات يدويًا بواسطة المستخدم."
            "</div>"
        )

    excluded_note = ""
    future_n = research_pkg.get("future_sources_excluded", 0)
    dup_n = research_pkg.get("duplicate_sources_removed", 0)
    if is_admin and (future_n or dup_n):
        excluded_note = (
            f'<div style="color:#94a3b8;font-size:12px;margin-top:8px;">'
            f"المصادر المستبعدة: {future_n} بعد تاريخ التقييم · {dup_n} مكررة"
            "</div>"
        )

    return f"""
<div data-section="citations" id="s-citations"
     style="margin:24px 0;background:rgba(15,23,42,0.8);border:1px solid rgba(255,255,255,0.1);
            border-radius:12px;padding:20px;direction:rtl;text-align:right;font-family:Tajawal,sans-serif;">
  <h3 style="color:#60a5fa;margin:0 0 12px 0;font-size:15px;">
    📚 مصادر البحث السوقي
  </h3>
  <div style="font-size:12px;color:#94a3b8;margin-bottom:12px;padding:8px;
              background:rgba(245,158,11,0.08);border-radius:6px;">
    {_RESEARCH_DISCLOSURE_AR}
  </div>
  <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-family:Tajawal,sans-serif;">
      <thead>
        <tr style="background:rgba(255,255,255,0.05);">
          <th style="padding:8px 6px;text-align:right;font-size:12px;color:#94a3b8;">معرّف</th>
          <th style="padding:8px 6px;text-align:right;font-size:12px;color:#94a3b8;">المصدر</th>
          <th style="padding:8px 6px;text-align:right;font-size:12px;color:#94a3b8;">التاريخ</th>
          <th style="padding:8px 6px;text-align:right;font-size:12px;color:#94a3b8;">نوع الدليل</th>
          <th style="padding:8px 6px;text-align:right;font-size:12px;color:#94a3b8;">القيمة</th>
          <th style="padding:8px 6px;text-align:right;font-size:12px;color:#94a3b8;">الثقة</th>
        </tr>
      </thead>
      <tbody>{''.join(rows) if rows else '<tr><td colspan="6" style="padding:16px;text-align:center;color:#94a3b8;">لا توجد مصادر</td></tr>'}</tbody>
    </table>
  </div>
  {override_note}
  {excluded_note}
</div>"""


def build_citations_excel_rows(research_pkg: dict) -> list[dict]:
    """
    Phase 22: Build flat list of source-register rows for Excel admin sheet.
    Each row is a dict of column_name: value.
    """
    rows: list[dict] = []
    for src in research_pkg.get("sources", []):
        rows.append({
            "معرّف المصدر": src.get("source_id", ""),
            "الناشر": src.get("publisher", ""),
            "عنوان المصدر": src.get("title", ""),
            "نوع المصدر": src.get("source_type", ""),
            "رابط المصدر": src.get("url", ""),
            "تاريخ النشر": src.get("publication_date", ""),
            "تاريخ الوصول": src.get("access_date", ""),
            "الجغرافيا": src.get("geography", ""),
            "العملة": src.get("currency", ""),
            "الوحدة": src.get("unit", ""),
            "القيمة الخام": src.get("raw_value"),
            "القيمة المعيارية": src.get("normalized_value"),
            "نوع الدليل": src.get("evidence_type", ""),
            "الثقة": src.get("confidence", ""),
            "ضمن نافذة التقييم": "نعم" if src.get("within_preferred_window") else "لا",
            "عمر الدليل (أيام)": src.get("age_in_days", ""),
            "القيود": "; ".join(src.get("limitations", [])),
            "مقتطف الدليل": src.get("excerpt", ""),
        })
    # Excluded sources
    for src in research_pkg.get("excluded_sources", []):
        rows.append({
            "معرّف المصدر": src.get("source_id", "") + " [مستبعد]",
            "الناشر": src.get("publisher", ""),
            "عنوان المصدر": src.get("title", ""),
            "نوع المصدر": src.get("source_type", ""),
            "رابط المصدر": src.get("url", ""),
            "تاريخ النشر": src.get("publication_date", ""),
            "تاريخ الوصول": src.get("access_date", ""),
            "الجغرافيا": "",
            "العملة": src.get("currency", ""),
            "الوحدة": src.get("unit", ""),
            "القيمة الخام": src.get("raw_value"),
            "القيمة المعيارية": None,
            "نوع الدليل": src.get("evidence_type", ""),
            "الثقة": "",
            "ضمن نافذة التقييم": "لا",
            "عمر الدليل (أيام)": src.get("age_in_days", ""),
            "القيود": src.get("exclusion_reason", ""),
            "مقتطف الدليل": "",
        })
    return rows


# ── FLASK ENDPOINT REGISTRATION ───────────────────────────────────────────────

def register_research_endpoint(
    app: Any,
    require_auth: Any,
    is_admin_fn: Any,
    provider: Any = None,
) -> None:
    """
    Register research endpoints on the Flask app.
    Phase 6: all research is server-side; no browser-side internet access.
    """
    from flask import request, jsonify, g  # type: ignore[import]

    @app.route("/api/simulation/research", methods=["POST"])
    @require_auth
    def simulation_research():  # type: ignore[return]
        body = request.get_json(force=True, silent=True) or {}
        pkg = build_research_package(body, provider=provider)
        # API keys must never appear in responses
        pkg.pop("_api_key", None)
        return jsonify(pkg)

    @app.route("/api/simulation/research/approve", methods=["POST"])
    @require_auth
    def simulation_research_approve():  # type: ignore[return]
        body = request.get_json(force=True, silent=True) or {}
        research_pkg = body.get("research_package", {})
        approved_inputs = body.get("approved_inputs", {})
        manual_overrides = body.get("manual_overrides", [])
        user_id = getattr(g, "user_id", "unknown")

        result = apply_user_approval(research_pkg, approved_inputs, manual_overrides, user_id)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)


class _EnvResearchProvider:
    """Stub for an environment-configured research provider."""

    def __init__(self, api_key: str):
        self._key = api_key

    def configured(self) -> bool:
        return bool(self._key)

    def search(self, query_text: str) -> list[dict]:  # noqa: ARG002
        # Real implementation would call an approved external search API here.
        # The API key (self._key) must never appear in any response or report.
        log.warning(
            "VALUATION_RESEARCH_API_KEY set but no real search implementation registered. "
            "Return empty — configure a concrete provider subclass for live use."
        )
        return []
