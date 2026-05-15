"""
mcp_bridge.py — Expert Smart MCP Bridge (Phase 16.0)

Exposes the Expert Smart valuation API as 10 Claude-callable MCP tools via FastMCP.
The bridge layer (ExpertSmartBridge) is kept independent of FastMCP so it can be
imported and tested without running the MCP server.

URL corrections vs. spec:
    POST /api/valuation/batch      (not /api/batch/valuate)
    GET  /api/valuation/batch/<id> (not /api/batch/status/{id})
    GET  /api/advisor/health       (not /api/health)

Tools:
    1.  health_check
    2.  evaluate_property
    3.  evaluate_land
    4.  search_comparables
    5.  analyze_portfolio
    6.  batch_valuate
    7.  get_batch_status
    8.  generate_report
    9.  audit_valuation
    10. dcf_analyze
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
from fastmcp import FastMCP


# ── Response wrapper ──────────────────────────────────────────────────────────

@dataclass
class APIResponse:
    """Standardised response envelope from the Expert Smart API."""

    success: bool
    status:  str
    data:    Optional[Dict[str, Any]] = field(default=None)
    error:   Optional[str]            = field(default=None)

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "status":  self.status,
            "data":    self.data,
            "error":   self.error,
        }


# ── Bridge class ──────────────────────────────────────────────────────────────

class ExpertSmartBridge:
    """
    Thin HTTP wrapper around the Expert Smart Flask API.

    All methods return an APIResponse.  Exceptions are caught and wrapped
    so callers always receive a structured object (never a raw exception).
    """

    def __init__(self, api_base: str = "http://localhost:5000") -> None:
        self.api_base = api_base.rstrip("/")
        self.client   = httpx.Client(timeout=30.0)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get(self, path: str) -> APIResponse:
        try:
            resp = self.client.get(f"{self.api_base}{path}")
            if resp.status_code == 200:
                return APIResponse(success=True, status="success", data=resp.json())
            return APIResponse(success=False, status="error",
                               error=f"HTTP {resp.status_code}")
        except Exception as exc:
            return APIResponse(success=False, status="unreachable", error=str(exc))

    def _post(self, path: str, payload: Dict) -> APIResponse:
        try:
            resp = self.client.post(f"{self.api_base}{path}", json=payload)
            if resp.status_code in (200, 201):
                result = resp.json()
                ok = result.get("status") in ("success", "completed")
                return APIResponse(success=ok, status=result.get("status", "unknown"),
                                   data=result)
            return APIResponse(success=False, status="error",
                               error=f"HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            return APIResponse(success=False, status="unreachable", error=str(exc))

    # ── Public methods ────────────────────────────────────────────────────────

    def health_check(self) -> APIResponse:
        """Check Expert Smart API health."""
        r = self._get("/api/advisor/health")
        if r.success:
            r.status = "healthy"
        elif r.status == "unreachable":
            pass  # keep "unreachable"
        else:
            r.status = "unhealthy"
        return r

    def evaluate_property(
        self,
        area_sqm:        float,
        location:        str,
        property_type:   str = "residential",
        primary_purpose: str = "market_value",
    ) -> APIResponse:
        """Evaluate a single property using Expert Smart's valuation engines."""
        payload = {
            "subject_property": {
                "property_type": property_type,
                "area_sqm":      area_sqm,
                "location":      location,
            },
            "filters":         {"governorate": location},
            "primary_purpose": primary_purpose,
        }
        return self._post("/api/valuation/full", payload)

    def evaluate_land(self, area_sqm: float, location: str) -> APIResponse:
        """Evaluate land — highest and best use analysis."""
        payload = {
            "subject_property": {
                "property_type": "land",
                "area_sqm":      area_sqm,
                "location":      location,
            }
        }
        return self._post("/api/valuation/land", payload)

    def search_comparables(
        self,
        property_type: str           = "residential",
        location:      Optional[str] = None,
        price_range:   Optional[tuple] = None,
    ) -> APIResponse:
        """Search comparable properties in the market feed."""
        filters: Dict[str, Any] = {"property_type": property_type}
        if location:
            filters["governorate"] = location
        if price_range:
            filters["price_range"] = list(price_range)
        return self._post("/api/comparables/search", {"filters": filters})

    def analyze_portfolio(self, properties: List[Dict]) -> APIResponse:
        """Analyse a real estate portfolio and return aggregate metrics."""
        payload = {
            "portfolio_name":  "MCP Portfolio",
            "properties":      properties,
            "generate_report": False,
        }
        return self._post("/api/valuation/portfolio", payload)

    def batch_valuate(self, properties: List[Dict]) -> APIResponse:
        """Valuate multiple properties in a single batch job."""
        payload = {
            "batch_name":      "MCP Batch",
            "properties":      properties,
            "generate_report": False,
        }
        return self._post("/api/valuation/batch", payload)

    def get_batch_status(self, batch_id: str) -> APIResponse:
        """Retrieve the result of a previously submitted batch job."""
        return self._get(f"/api/valuation/batch/{batch_id}")

    def generate_report(
        self,
        area_sqm:      float,
        location:      str,
        property_type: str = "residential",
    ) -> APIResponse:
        """Generate an Excel valuation report and return its download URL."""
        payload = {
            "subject_property": {
                "property_type": property_type,
                "area_sqm":      area_sqm,
                "location":      location,
            },
            "filters": {"governorate": location},
        }
        return self._post("/api/valuation/report", payload)

    def audit_valuation(
        self,
        area_sqm:      float,
        location:      str,
        property_type: str = "residential",
    ) -> APIResponse:
        """Run a quality-audit pass on a property valuation."""
        payload = {
            "subject_property": {
                "property_type": property_type,
                "area_sqm":      area_sqm,
                "location":      location,
            }
        }
        return self._post("/api/valuation/audit", payload)

    def dcf_analyze(
        self,
        discount_rate:       float,
        holding_period:      int,
        annual_projections:  List[Dict],
    ) -> APIResponse:
        """Perform a Discounted Cash Flow (DCF) analysis."""
        payload = {
            "dcf_assumptions": {
                "discount_rate":      discount_rate,
                "holding_period":     holding_period,
                "annual_projections": annual_projections,
            }
        }
        return self._post("/api/valuation/dcf", payload)


# ── FastMCP server ────────────────────────────────────────────────────────────

mcp    = FastMCP("expert_smart")
bridge = ExpertSmartBridge()


def _dump(r: APIResponse) -> str:
    return json.dumps(r.to_dict(), ensure_ascii=False, indent=2)


@mcp.tool()
def health_check() -> str:
    """تحقق من حالة نظام Expert Smart"""
    return _dump(bridge.health_check())


@mcp.tool()
def evaluate_property(
    area_sqm:        float,
    location:        str,
    property_type:   str = "residential",
    primary_purpose: str = "market_value",
) -> str:
    """
    قيّم عقار باستخدام محركات التقييم المتقدمة

    Args:
        area_sqm: مساحة العقار بالمتر المربع
        location: الموقع (المحافظة)
        property_type: نوع العقار (residential, commercial, land)
        primary_purpose: غرض التقييم (market_value, insurance, mortgage, ifrs13)
    """
    return _dump(bridge.evaluate_property(area_sqm, location, property_type, primary_purpose))


@mcp.tool()
def evaluate_land(area_sqm: float, location: str) -> str:
    """قيّم أرض (تحليل أفضل استخدام)"""
    return _dump(bridge.evaluate_land(area_sqm, location))


@mcp.tool()
def search_comparables(
    property_type: str = "residential",
    location:      str = "",
) -> str:
    """ابحث عن عقارات قابلة للمقارنة"""
    return _dump(bridge.search_comparables(property_type, location or None))


@mcp.tool()
def analyze_portfolio(properties: str) -> str:
    """
    حلل محفظة عقارات

    Args:
        properties: JSON array من العقارات (property_id, property_type, valuation_value, annual_noi)
    """
    try:
        props = json.loads(properties)
        return _dump(bridge.analyze_portfolio(props))
    except Exception as exc:
        return json.dumps({"success": False, "status": "error", "error": str(exc)},
                          ensure_ascii=False)


@mcp.tool()
def batch_valuate(properties: str) -> str:
    """
    قيّم عدة عقارات بشكل متزامن

    Args:
        properties: JSON array من العقارات مع input_data
    """
    try:
        props = json.loads(properties)
        return _dump(bridge.batch_valuate(props))
    except Exception as exc:
        return json.dumps({"success": False, "status": "error", "error": str(exc)},
                          ensure_ascii=False)


@mcp.tool()
def get_batch_status(batch_id: str) -> str:
    """احصل على حالة معالجة دفعة التقييم"""
    return _dump(bridge.get_batch_status(batch_id))


@mcp.tool()
def generate_report(
    area_sqm:      float,
    location:      str,
    property_type: str = "residential",
) -> str:
    """أنشئ تقرير Excel للعقار"""
    return _dump(bridge.generate_report(area_sqm, location, property_type))


@mcp.tool()
def audit_valuation(
    area_sqm:      float,
    location:      str,
    property_type: str = "residential",
) -> str:
    """شغّل تدقيق جودة على التقييم"""
    return _dump(bridge.audit_valuation(area_sqm, location, property_type))


@mcp.tool()
def dcf_analyze(
    discount_rate:      float,
    holding_period:     int,
    annual_projections: str,
) -> str:
    """
    حلل نموذج DCF (القيمة الحالية للتدفقات النقدية)

    Args:
        discount_rate: معدل الخصم (مثال: 0.12)
        holding_period: فترة الاحتفاظ بالسنوات
        annual_projections: JSON array لكل سنة مع noi و capex
    """
    try:
        projections = json.loads(annual_projections)
        return _dump(bridge.dcf_analyze(discount_rate, holding_period, projections))
    except Exception as exc:
        return json.dumps({"success": False, "status": "error", "error": str(exc)},
                          ensure_ascii=False)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio as _asyncio
    tools = [t.name for t in _asyncio.run(mcp.list_tools())]
    print("Expert Smart MCP Bridge starting...")
    print(f"Available tools ({len(tools)}):")
    for i, name in enumerate(tools, 1):
        print(f"  {i:2d}. {name}")
    print()
    mcp.run()
