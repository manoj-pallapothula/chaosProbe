"""
Prometheus client — queries Prometheus HTTP API for metrics during experiments.
"""
from __future__ import annotations

from typing import Any
import httpx

from chaosProbe.utils.logger import get_logger

logger = get_logger(__name__)


class PrometheusClient:
    """Thin client for querying Prometheus instant and range queries."""

    def __init__(self, base_url: str = "http://localhost:9090", timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def query(self, promql: str) -> float | None:
        """
        Run an instant query and return the first scalar value.
        Returns None if the query fails or returns no data.
        """
        url = f"{self.base_url}/api/v1/query"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params={"query": promql})
                resp.raise_for_status()
                data = resp.json()
                return self._extract_value(data)
        except Exception as exc:
            logger.warning(f"[prometheus] Query failed: {promql} — {exc}")
            return None

    def query_range(
        self,
        promql: str,
        start: float,
        end: float,
        step: str = "15s",
    ) -> list[tuple[float, float]]:
        """
        Run a range query and return list of (timestamp, value) tuples.
        """
        url = f"{self.base_url}/api/v1/query_range"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params={
                    "query": promql,
                    "start": start,
                    "end": end,
                    "step": step,
                })
                resp.raise_for_status()
                data = resp.json()
                return self._extract_range(data)
        except Exception as exc:
            logger.warning(f"[prometheus] Range query failed: {promql} — {exc}")
            return []

    def is_healthy(self) -> bool:
        """Check if Prometheus is reachable."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/-/healthy")
                return resp.status_code == 200
        except Exception:
            return False

    def _extract_value(self, data: dict[str, Any]) -> float | None:
        try:
            results = data["data"]["result"]
            if not results:
                return None
            value = results[0]["value"][1]
            return float(value)
        except (KeyError, IndexError, ValueError):
            return None

    def _extract_range(self, data: dict[str, Any]) -> list[tuple[float, float]]:
        try:
            results = data["data"]["result"]
            if not results:
                return []
            values = results[0]["values"]
            return [(float(ts), float(val)) for ts, val in values]
        except (KeyError, IndexError, ValueError):
            return []