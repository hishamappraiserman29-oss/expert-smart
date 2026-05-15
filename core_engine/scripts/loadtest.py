"""
loadtest.py — Load Testing Utility (Phase 39)

Multi-threaded load generator with response time statistics.
"""

from __future__ import annotations

import logging
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LoadTester:
    """Multi-threaded load tester with percentile statistics."""

    def __init__(self, api_url: str = "http://localhost:5000", num_workers: int = 10) -> None:
        self.api_url = api_url
        self.num_workers = num_workers
        self.results: List[Dict[str, Any]] = []
        logger.info("Load Tester initialized (workers=%d, url=%s)", num_workers, api_url)

    def test_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            import requests
            start = time.perf_counter()
            if method == "GET":
                response = requests.get(f"{self.api_url}{endpoint}", timeout=10)
            elif method == "POST":
                response = requests.post(f"{self.api_url}{endpoint}", json=data, timeout=10)
            else:
                return {"endpoint": endpoint, "error": f"Unsupported method: {method}", "success": False}
            elapsed = time.perf_counter() - start
            return {
                "endpoint": endpoint,
                "status": response.status_code,
                "response_time": elapsed,
                "success": response.status_code < 400,
            }
        except Exception as exc:
            return {"endpoint": endpoint, "error": str(exc), "success": False, "response_time": 0.0}

    def run_load_test(
        self,
        endpoint: str,
        num_requests: int = 100,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info("Running load test: %d requests to %s", num_requests, endpoint)
        results: List[Dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self.num_workers) as pool:
            futures = [
                pool.submit(self.test_endpoint, endpoint, method, data)
                for _ in range(num_requests)
            ]
            for fut in as_completed(futures):
                results.append(fut.result())

        times = [r["response_time"] for r in results if "response_time" in r and r["response_time"] > 0]
        success_count = sum(1 for r in results if r.get("success", False))

        p95 = 0.0
        if len(times) >= 20:
            p95 = statistics.quantiles(times, n=20)[18]
        elif times:
            p95 = max(times)

        summary: Dict[str, Any] = {
            "endpoint": endpoint,
            "total_requests": num_requests,
            "successful": success_count,
            "failed": num_requests - success_count,
            "success_rate": round(success_count / num_requests * 100, 2),
            "avg_response_time": round(statistics.mean(times), 4) if times else 0.0,
            "min_response_time": round(min(times), 4) if times else 0.0,
            "max_response_time": round(max(times), 4) if times else 0.0,
            "p95_response_time": round(p95, 4),
        }
        self.results.append(summary)
        return summary


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    tester = LoadTester()
    result = tester.run_load_test("/api/health", num_requests=20)
    import json
    print(json.dumps(result, indent=2))
