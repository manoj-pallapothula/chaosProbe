"""
SLO Monitor — scrapes Prometheus during an experiment and checks
error rate, p99 latency, and availability against defined thresholds.
Signals the orchestrator to rollback if any SLO is breached.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chaosProbe.engine.experiment import SLOConfig
from chaosProbe.monitoring.prometheus_client import PrometheusClient
from chaosProbe.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SLOBreachEvent:
    slo_name: str
    threshold: float
    actual: float
    timestamp: float


@dataclass
class SLOReport:
    breached: bool = False
    breach_events: list[SLOBreachEvent] = field(default_factory=list)
    samples: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "breached": self.breached,
            "breach_events": [
                {
                    "slo_name": e.slo_name,
                    "threshold": e.threshold,
                    "actual": e.actual,
                    "timestamp": e.timestamp,
                }
                for e in self.breach_events
            ],
            "samples": self.samples,
        }


class SLOMonitor:
    """
    Checks SLOs against live Prometheus metrics.
    Used by the Orchestrator during an experiment run.
    """

    def __init__(self, prometheus_client: PrometheusClient):
        self.prom = prometheus_client
        self.report = SLOReport()

    def check(self, slo: SLOConfig) -> bool:
        """
        Run all SLO checks. Returns True if any SLO is breached.
        """
        import time
        breached = False
        sample: dict[str, Any] = {"timestamp": time.time()}

        # ── Error rate check ─────────────────────────────────────────────────
        error_rate = self._get_error_rate()
        sample["error_rate_percent"] = error_rate
        if error_rate is not None:
            if error_rate > slo.error_rate_percent:
                logger.warning(
                    f"[slo] Error rate breached: {error_rate:.2f}% > {slo.error_rate_percent}%"
                )
                self._record_breach("error_rate_percent", slo.error_rate_percent, error_rate)
                breached = True

        # ── Latency p99 check ────────────────────────────────────────────────
        latency_p99 = self._get_latency_p99()
        sample["latency_p99_ms"] = latency_p99
        if latency_p99 is not None:
            if latency_p99 > slo.latency_p99_ms:
                logger.warning(
                    f"[slo] Latency p99 breached: {latency_p99:.0f}ms > {slo.latency_p99_ms}ms"
                )
                self._record_breach("latency_p99_ms", slo.latency_p99_ms, latency_p99)
                breached = True

        # ── Availability check ───────────────────────────────────────────────
        availability = self._get_availability()
        sample["availability_percent"] = availability
        if availability is not None:
            if availability < slo.availability_percent:
                logger.warning(
                    f"[slo] Availability breached: {availability:.2f}% < {slo.availability_percent}%"
                )
                self._record_breach("availability_percent", slo.availability_percent, availability)
                breached = True

        self.report.samples.append(sample)
        if breached:
            self.report.breached = True

        return breached

    def _get_error_rate(self) -> float | None:
        """Error rate as a percentage (0-100)."""
        result = self.prom.query(
            'sum(rate(target_requests_total{status="500"}[1m])) / '
            'sum(rate(target_requests_total[1m])) * 100'
        )
        return result

    def _get_latency_p99(self) -> float | None:
        """p99 latency in milliseconds."""
        result = self.prom.query(
            'histogram_quantile(0.99, '
            'sum(rate(target_request_duration_seconds_bucket[1m])) by (le)) * 1000'
        )
        return result

    def _get_availability(self) -> float | None:
        """Availability as a percentage (0-100)."""
        result = self.prom.query(
            'sum(rate(target_requests_total{status="200"}[1m])) / '
            'sum(rate(target_requests_total[1m])) * 100'
        )
        return result

    def _record_breach(self, slo_name: str, threshold: float, actual: float) -> None:
        import time
        self.report.breach_events.append(
            SLOBreachEvent(
                slo_name=slo_name,
                threshold=threshold,
                actual=actual,
                timestamp=time.time(),
            )
        )