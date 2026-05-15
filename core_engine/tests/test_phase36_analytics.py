"""
test_phase36_analytics.py — Phase 36: Advanced Analytics & BI Tests

Test groups:
  A — AnalyticsEngine (A01-A12)
  B — DashboardSystem (B01-B10)
  C — ForecastingEngine (C01-C10)
  D — MarketIntelligence (D01-D08)
  E — PortfolioRiskAnalytics (E01-E10)
"""

import sys
import os
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analytics.analytics_engine import (
    AnalyticsEngine, MetricType, TimeGranularity,
)
from analytics.dashboard_system import (
    DashboardSystem, DashboardType, WidgetType, DashboardWidget,
)
from analytics.forecasting import ForecastingEngine
from analytics.market_intelligence import MarketIntelligence, MarketSegment
from analytics.portfolio_risk import PortfolioRiskAnalytics, RiskLevel


# ---------------------------------------------------------------------------
# Fixtures — fresh instance per test class
# ---------------------------------------------------------------------------

@pytest.fixture
def ae():
    return AnalyticsEngine()


@pytest.fixture
def ds():
    return DashboardSystem()


@pytest.fixture
def fe():
    return ForecastingEngine()


@pytest.fixture
def mi():
    return MarketIntelligence()


@pytest.fixture
def pra():
    return PortfolioRiskAnalytics()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_fill(ae, mid, n=5, base=100.0):
    ae.register_metric(mid, f"Metric {mid}", MetricType.COUNT, "desc", unit="units")
    for i in range(n):
        ae.record_data_point(mid, base + i)
    return ae.metrics[mid]


def _make_widget(wid, wtype=WidgetType.METRIC_CARD):
    return DashboardWidget(
        widget_id=wid, widget_type=wtype,
        title=f"Widget {wid}", metric_ids=["M1"],
    )


def _record_trend(mi, tid, seg=MarketSegment.RESIDENTIAL, pct=5.0, location="Cairo"):
    current = 1000.0 * (1 + pct / 100)
    return mi.record_market_trend(
        trend_id=tid, segment=seg, location=location,
        metric_name="Price", current_value=current, previous_value=1000.0,
    )


def _make_assets(n=4, include_illiquid=False):
    assets = [{"value": 2_500_000, "liquidity": "high"} for _ in range(n - 1)]
    if include_illiquid:
        assets.append({"value": 500_000, "liquidity": "low"})
    else:
        assets.append({"value": 2_500_000, "liquidity": "high"})
    return assets


# ---------------------------------------------------------------------------
# A — AnalyticsEngine
# ---------------------------------------------------------------------------

class TestAnalyticsEngine:

    def test_A01_register_metric(self, ae):
        m = ae.register_metric("M1", "Test Count", MetricType.COUNT, "A count metric")
        assert m.metric_id == "M1"
        assert m.metric_type == MetricType.COUNT

    def test_A02_metric_stored(self, ae):
        ae.register_metric("M2", "Sum", MetricType.SUM, "desc")
        assert "M2" in ae.metrics

    def test_A03_record_data_point_returns_true(self, ae):
        ae.register_metric("M3", "Rate", MetricType.RATE, "desc")
        result = ae.record_data_point("M3", 42.0)
        assert result is True

    def test_A04_record_unknown_metric_returns_false(self, ae):
        assert ae.record_data_point("NONEXISTENT", 0.0) is False

    def test_A05_data_point_stored(self, ae):
        ae.register_metric("M5", "Val", MetricType.AVERAGE, "desc")
        ae.record_data_point("M5", 99.0)
        assert ae.metrics["M5"].data_points[0].value == pytest.approx(99.0)

    def test_A06_statistics_empty_metric(self, ae):
        ae.register_metric("M6", "Empty", MetricType.COUNT, "desc")
        stats = ae.get_metric_statistics("M6")
        assert stats["data_points"] == 0

    def test_A07_statistics_min_max_avg(self, ae):
        _register_and_fill(ae, "M7", n=5, base=10.0)
        stats = ae.get_metric_statistics("M7")
        assert stats["min"] == pytest.approx(10.0)
        assert stats["max"] == pytest.approx(14.0)
        assert stats["average"] == pytest.approx(12.0)

    def test_A08_statistics_stdev_with_multiple_points(self, ae):
        _register_and_fill(ae, "M8", n=5)
        stats = ae.get_metric_statistics("M8")
        assert "stdev" in stats

    def test_A09_time_series_daily_aggregation(self, ae):
        ae.register_metric("M9", "Daily", MetricType.SUM, "desc")
        now = datetime.utcnow()
        for i in range(3):
            ae.record_data_point("M9", float(i + 1),
                                 timestamp=now - timedelta(days=i))
        ts = ae.get_time_series("M9", granularity=TimeGranularity.DAILY)
        assert len(ts) >= 1
        assert "value" in ts[0]

    def test_A10_time_series_respects_start_end(self, ae):
        ae.register_metric("M10", "Range", MetricType.COUNT, "desc")
        old = datetime(2020, 1, 1)
        ae.record_data_point("M10", 999.0, timestamp=old)
        ae.record_data_point("M10", 1.0)
        ts = ae.get_time_series("M10", start_time=datetime(2024, 1, 1))
        values = [p["value"] for p in ts]
        assert 999.0 not in values

    def test_A11_engine_statistics(self, ae):
        ae.register_metric("M11A", "A", MetricType.COUNT, "desc")
        ae.register_metric("M11B", "B", MetricType.SUM, "desc")
        stats = ae.get_engine_statistics()
        assert stats["total_metrics"] == 2
        assert "metrics_by_type" in stats

    def test_A12_max_data_points_pruned(self, ae):
        ae.register_metric("M12", "Big", MetricType.COUNT, "desc")
        ae._MAX_DATA_POINTS = 5
        for i in range(8):
            ae.record_data_point("M12", float(i))
        assert len(ae.metrics["M12"].data_points) <= 5


# ---------------------------------------------------------------------------
# B — DashboardSystem
# ---------------------------------------------------------------------------

class TestDashboardSystem:

    def test_B01_create_dashboard(self, ds):
        d = ds.create_dashboard("D1", "Executive", DashboardType.EXECUTIVE,
                                "Exec dash", "USR1")
        assert d.dashboard_id == "D1"
        assert d.dashboard_type == DashboardType.EXECUTIVE

    def test_B02_dashboard_stored(self, ds):
        ds.create_dashboard("D2", "Ops", DashboardType.OPERATIONAL, "desc", "USR1")
        assert "D2" in ds.dashboards

    def test_B03_add_widget(self, ds):
        ds.create_dashboard("D3", "Portfolio", DashboardType.PORTFOLIO, "desc", "USR1")
        w = _make_widget("W1")
        result = ds.add_widget("D3", w)
        assert result is True
        assert len(ds.dashboards["D3"].widgets) == 1

    def test_B04_add_widget_unknown_dashboard(self, ds):
        assert ds.add_widget("NONEXISTENT", _make_widget("W0")) is False

    def test_B05_get_user_dashboards(self, ds):
        ds.create_dashboard("D5A", "Dash A", DashboardType.CUSTOM, "desc", "USR2")
        ds.create_dashboard("D5B", "Dash B", DashboardType.MARKET, "desc", "USR2")
        ds.create_dashboard("D5C", "Dash C", DashboardType.COMPLIANCE, "desc", "USR9")
        user_dashes = ds.get_user_dashboards("USR2")
        assert len(user_dashes) == 2

    def test_B06_get_dashboards_by_type(self, ds):
        ds.create_dashboard("D6A", "Exec A", DashboardType.EXECUTIVE, "desc", "USR1")
        ds.create_dashboard("D6B", "Exec B", DashboardType.EXECUTIVE, "desc", "USR1")
        ds.create_dashboard("D6C", "Ops", DashboardType.OPERATIONAL, "desc", "USR1")
        execs = ds.get_dashboards_by_type(DashboardType.EXECUTIVE)
        assert len(execs) == 2

    def test_B07_record_view_increments(self, ds):
        ds.create_dashboard("D7", "Viewed", DashboardType.PERFORMANCE, "desc", "USR1")
        ds.record_view("D7")
        ds.record_view("D7")
        assert ds.dashboards["D7"].view_count == 2

    def test_B08_share_dashboard(self, ds):
        ds.create_dashboard("D8", "Shared", DashboardType.COMPLIANCE, "desc", "USR1")
        result = ds.share_dashboard("D8", ["USR2", "USR3"])
        assert result is True
        assert ds.dashboards["D8"].is_shared is True
        assert "USR2" in ds.dashboards["D8"].shared_with

    def test_B09_pin_dashboard(self, ds):
        ds.create_dashboard("D9", "Pinned", DashboardType.MARKET, "desc", "USR1")
        assert ds.dashboards["D9"].is_pinned is False
        ds.pin_dashboard("D9")
        assert ds.dashboards["D9"].is_pinned is True

    def test_B10_statistics(self, ds):
        ds.create_dashboard("D10A", "A", DashboardType.EXECUTIVE, "desc", "USR1")
        ds.create_dashboard("D10B", "B", DashboardType.OPERATIONAL, "desc", "USR1")
        ds.add_widget("D10A", _make_widget("WX"))
        stats = ds.get_statistics()
        assert stats["total_dashboards"] == 2
        assert stats["total_widgets"] == 1


# ---------------------------------------------------------------------------
# C — ForecastingEngine
# ---------------------------------------------------------------------------

class TestForecastingEngine:

    def test_C01_create_model(self, fe):
        m = fe.create_forecast_model("FM1", "Linear Forecast",
                                     "linear_regression", "M1", forecast_horizon=30)
        assert m.model_id == "FM1"
        assert m.model_type == "linear_regression"

    def test_C02_invalid_model_type_raises(self, fe):
        with pytest.raises(ValueError):
            fe.create_forecast_model("FM-BAD", "Bad", "random_forest", "M1")

    def test_C03_all_valid_model_types(self, fe):
        for mtype in ["linear_regression", "arima", "prophet", "lstm", "ensemble"]:
            fe.create_forecast_model(f"FM-{mtype}", f"Model {mtype}",
                                     mtype, "M1")
        assert fe.count_models() >= 5

    def test_C04_train_model_success(self, fe):
        fe.create_forecast_model("FM2", "ARIMA", "arima", "M2", forecast_horizon=14)
        result = fe.train_model("FM2", [100.0, 102.0, 98.0, 105.0, 103.0])
        assert result is True
        assert fe.models["FM2"].historical_data_points == 5

    def test_C05_train_model_too_few_data_points(self, fe):
        fe.create_forecast_model("FM3", "LSTM", "lstm", "M3")
        result = fe.train_model("FM3", [100.0])
        assert result is False

    def test_C06_generate_forecast_correct_horizon(self, fe):
        fe.create_forecast_model("FM4", "Prophet", "prophet", "M4", forecast_horizon=7)
        fe.train_model("FM4", [100.0, 101.0, 99.0, 102.0])
        fc = fe.generate_forecast("FM4", "FC-001")
        assert fc is not None
        assert len(fc.forecasted_values) == 7

    def test_C07_forecast_confidence_intervals_match_horizon(self, fe):
        fe.create_forecast_model("FM5", "Ens", "ensemble", "M5", forecast_horizon=10)
        fe.train_model("FM5", [50.0, 55.0, 52.0, 58.0])
        fc = fe.generate_forecast("FM5", "FC-002")
        assert len(fc.confidence_intervals) == 10

    def test_C08_forecast_stored(self, fe):
        fe.create_forecast_model("FM6", "Lin", "linear_regression", "M6")
        fe.train_model("FM6", [1.0, 2.0, 3.0, 4.0])
        fe.generate_forecast("FM6", "FC-003")
        assert "FC-003" in fe.forecasts

    def test_C09_accuracy_after_training(self, fe):
        fe.create_forecast_model("FM7", "ARIMA2", "arima", "M7")
        fe.train_model("FM7", [100.0] * 20)
        acc = fe.get_forecast_accuracy("FM7")
        assert 0.0 < acc <= 1.0

    def test_C10_deactivate_model(self, fe):
        fe.create_forecast_model("FM8", "LSTM2", "lstm", "M8")
        fe.deactivate_model("FM8")
        active = fe.list_active_models()
        assert not any(m.model_id == "FM8" for m in active)


# ---------------------------------------------------------------------------
# D — MarketIntelligence
# ---------------------------------------------------------------------------

class TestMarketIntelligence:

    def test_D01_record_trend_stored(self, mi):
        t = _record_trend(mi, "T1")
        assert mi.trends["T1"] is not None

    def test_D02_trend_direction_up(self, mi):
        t = _record_trend(mi, "T2", pct=10.0)
        assert t.trend_direction == "up"

    def test_D03_trend_direction_down(self, mi):
        t = mi.record_market_trend(
            "T3", MarketSegment.COMMERCIAL, "Cairo", "Price",
            current_value=900.0, previous_value=1000.0,
        )
        assert t.trend_direction == "down"

    def test_D04_trend_direction_stable(self, mi):
        t = mi.record_market_trend(
            "T4", MarketSegment.RESIDENTIAL, "Cairo", "Price",
            current_value=1005.0, previous_value=1000.0,
        )
        assert t.trend_direction == "stable"

    def test_D05_sentiment_bullish(self, mi):
        t = _record_trend(mi, "T5", pct=10.0)
        assert t.market_sentiment == "bullish"

    def test_D06_sentiment_bearish(self, mi):
        t = mi.record_market_trend(
            "T6", MarketSegment.INDUSTRIAL, "Alexandria", "Price",
            current_value=880.0, previous_value=1000.0,
        )
        assert t.market_sentiment == "bearish"

    def test_D07_get_trends_by_segment(self, mi):
        _record_trend(mi, "T7A", seg=MarketSegment.RESIDENTIAL)
        _record_trend(mi, "T7B", seg=MarketSegment.RESIDENTIAL)
        _record_trend(mi, "T7C", seg=MarketSegment.COMMERCIAL)
        res = mi.get_trends_by_segment(MarketSegment.RESIDENTIAL)
        assert len(res) == 2

    def test_D08_market_summary(self, mi):
        _record_trend(mi, "T8A", pct=8.0)
        _record_trend(mi, "T8B", pct=-7.0)
        summary = mi.get_market_summary()
        assert "total_trends" in summary
        assert summary["total_trends"] == 2


# ---------------------------------------------------------------------------
# E — PortfolioRiskAnalytics
# ---------------------------------------------------------------------------

class TestPortfolioRiskAnalytics:

    def test_E01_assess_low_risk(self, pra):
        assets = _make_assets(4)
        result = pra.assess_portfolio_risk("P1", "T1", 10_000_000, assets)
        assert result.overall_risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)

    def test_E02_high_concentration_triggers_recommendation(self, pra):
        assets = [
            {"value": 9_000_000, "liquidity": "high"},
            {"value": 1_000_000, "liquidity": "high"},
        ]
        result = pra.assess_portfolio_risk("P2", "T1", 10_000_000, assets)
        assert any("concentration" in r.lower() for r in result.recommendations)

    def test_E03_illiquid_assets_raise_liquidity_risk(self, pra):
        assets = _make_assets(4, include_illiquid=True)
        result = pra.assess_portfolio_risk("P3", "T1", 10_000_000, assets)
        assert result.liquidity_risk > 0

    def test_E04_var_95_less_than_var_99(self, pra):
        assets = _make_assets(4)
        result = pra.assess_portfolio_risk("P4", "T1", 10_000_000, assets)
        assert result.var_95 < result.var_99

    def test_E05_var_positive(self, pra):
        assets = _make_assets(3)
        result = pra.assess_portfolio_risk("P5", "T1", 5_000_000, assets)
        assert result.var_95 > 0

    def test_E06_to_dict_structure(self, pra):
        assets = _make_assets(2)
        result = pra.assess_portfolio_risk("P6", "T1", 2_000_000, assets)
        d = result.to_dict()
        assert "risk_scores" in d
        assert "var_95" in d
        assert "overall_risk_level" in d

    def test_E07_assessment_stored(self, pra):
        assets = _make_assets(2)
        pra.assess_portfolio_risk("P7", "T1", 2_000_000, assets)
        assert "P7" in pra.assessments

    def test_E08_high_risk_portfolios_filter(self, pra):
        # Very concentrated portfolio → HIGH or CRITICAL
        assets = [{"value": 9_900_000, "liquidity": "low"},
                  {"value": 100_000, "liquidity": "low"}]
        pra.assess_portfolio_risk("P8", "T1", 10_000_000, assets)
        high_risk = pra.get_high_risk_portfolios()
        assert any(p.portfolio_id == "P8" for p in high_risk)

    def test_E09_risk_distribution(self, pra):
        assets = _make_assets(4)
        pra.assess_portfolio_risk("P9A", "T2", 5_000_000, assets)
        pra.assess_portfolio_risk("P9B", "T2", 5_000_000, assets)
        dist = pra.get_risk_distribution()
        assert "total" in dist
        assert dist["total"] == 2

    def test_E10_empty_assets(self, pra):
        result = pra.assess_portfolio_risk("P10", "T1", 0.0, [])
        assert result.number_of_assets == 0
        assert result.var_95 == 0.0
