"""Tests for SLOMonitor."""
from unittest.mock import patch, MagicMock
import pytest

from chaosProbe.monitoring.slo_monitor import SLOMonitor, SLOReport
from chaosProbe.engine.experiment import SLOConfig
from chaosProbe.monitoring.prometheus_client import PrometheusClient


class TestSLOMonitor:
    def _make_monitor(self, query_values: dict = {}):
        prom = MagicMock(spec=PrometheusClient)
        def side_effect(promql):
            for key, val in query_values.items():
                if key in promql:
                    return val
            return None
        prom.query.side_effect = side_effect
        return SLOMonitor(prometheus_client=prom)

    def _make_slo(self, **kwargs):
        defaults = dict(
            error_rate_percent=5.0,
            latency_p99_ms=500.0,
            availability_percent=95.0,
        )
        defaults.update(kwargs)
        return SLOConfig(**defaults)

    def test_no_breach_when_metrics_healthy(self):
        monitor = self._make_monitor({
            "500": 1.0,           # error rate 1% — under 5% threshold
            "quantile": 200.0,    # p99 200ms — under 500ms threshold
            "200": 99.0,          # availability 99% — over 95% threshold
        })
        slo = self._make_slo()
        breached = monitor.check(slo)
        assert breached is False
        assert monitor.report.breached is False

    def test_breach_on_high_error_rate(self):
        monitor = self._make_monitor({
            "500": 10.0,          # error rate 10% — over 5% threshold
            "quantile": 200.0,
            "200": 90.0,
        })
        slo = self._make_slo(error_rate_percent=5.0)
        breached = monitor.check(slo)
        assert breached is True
        assert monitor.report.breached is True
        names = [e.slo_name for e in monitor.report.breach_events]
        assert "error_rate_percent" in names

    def test_breach_on_high_latency(self):
        monitor = self._make_monitor({
            "500": 1.0,
            "quantile": 800.0,    # p99 800ms — over 500ms threshold
            "200": 99.0,
        })
        slo = self._make_slo(latency_p99_ms=500.0)
        breached = monitor.check(slo)
        assert breached is True
        names = [e.slo_name for e in monitor.report.breach_events]
        assert "latency_p99_ms" in names

    def test_breach_on_low_availability(self):
        monitor = self._make_monitor({
            "500": 1.0,
            "quantile": 200.0,
            "200": 80.0,          # availability 80% — under 95% threshold
        })
        slo = self._make_slo(availability_percent=95.0)
        breached = monitor.check(slo)
        assert breached is True
        names = [e.slo_name for e in monitor.report.breach_events]
        assert "availability_percent" in names

    def test_no_breach_when_metrics_unavailable(self):
        monitor = self._make_monitor({})  # all queries return None
        slo = self._make_slo()
        breached = monitor.check(slo)
        assert breached is False

    def test_samples_recorded(self):
        monitor = self._make_monitor({
            "500": 1.0,
            "quantile": 200.0,
            "200": 99.0,
        })
        slo = self._make_slo()
        monitor.check(slo)
        monitor.check(slo)
        assert len(monitor.report.samples) == 2

    def test_report_to_dict(self):
        monitor = self._make_monitor({
            "500": 10.0,
            "quantile": 200.0,
            "200": 99.0,
        })
        slo = self._make_slo()
        monitor.check(slo)
        report = monitor.report.to_dict()
        assert "breached" in report
        assert "breach_events" in report
        assert "samples" in report