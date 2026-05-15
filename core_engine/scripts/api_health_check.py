"""
api_health_check.py — API Hardening Health Monitor
Run standalone to verify all hardening components import and initialise correctly.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CHECKS = []


def _check(name: str, fn):
    try:
        result = fn()
        CHECKS.append((name, True, result or "OK"))
    except Exception as exc:
        CHECKS.append((name, False, str(exc)))


def main() -> None:
    print("[api-health] Running API hardening health checks ...")

    _check("resilience imports", lambda: (
        __import__("api.resilience", fromlist=["RetryPolicy", "CircuitBreaker"])
        and "RetryPolicy imported"
    ))

    _check("connection_manager", lambda: (
        __import__("api.connection_manager", fromlist=["get_connection_manager"])
        .get_connection_manager()
        .get_stats()["total_acquired"] == 0
        and "ConnectionManager ready"
    ))

    _check("request_deduplication", lambda: (
        __import__("api.request_deduplication", fromlist=["RequestDeduplicator"])
        .RequestDeduplicator()
        .register_request("health-check-key", {})
        and "Deduplicator ready"
    ))

    _check("response_formatter", lambda: (
        __import__("api.response_formatter", fromlist=["ResponseFormatter"])
        .ResponseFormatter()
        .success(data={"check": True})
        .to_dict()["status"] == "success"
        and "ResponseFormatter ready"
    ))

    _check("error_handler", lambda: (
        __import__("api.error_handler", fromlist=["ValidationError"])
        .ValidationError("field", "msg")
        .status_code == 400
        and "ErrorHandler ready"
    ))

    _check("observability", lambda: (
        __import__("api.observability", fromlist=["StructuredLogger"])
        .StructuredLogger("health")
        and "StructuredLogger ready"
    ))

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    failed = len(CHECKS) - passed

    print()
    for name, ok, msg in CHECKS:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")

    print()
    print(f"[api-health] Results: {passed} pass, {failed} fail out of {len(CHECKS)} checks")

    if failed:
        sys.exit(1)
    print("[api-health] All checks passed.")


if __name__ == "__main__":
    main()
