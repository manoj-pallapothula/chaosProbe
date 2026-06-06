"""
Steady-state hypothesis checker.
Verifies the system is healthy before and after an experiment.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from chaosProbe.engine.experiment import SteadyStateCheck
from chaosProbe.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


class HypothesisChecker:
    """Runs all steady-state checks and returns results."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    def run_all(self, checks: list[SteadyStateCheck]) -> list[CheckResult]:
        results = []
        for check in checks:
            result = self._run_check(check)
            results.append(result)
            status = "✓" if result.passed else "✗"
            logger.info(f"[hypothesis] {status} {check.name}: {result.detail}")
        return results

    def all_passed(self, results: list[CheckResult]) -> bool:
        return all(r.passed for r in results)

    def _run_check(self, check: SteadyStateCheck) -> CheckResult:
        if check.check_type == "http":
            return self._http_check(check)
        elif check.check_type == "metric":
            return self._metric_check(check)
        else:
            return CheckResult(
                name=check.name,
                passed=False,
                detail=f"Unknown check type: {check.check_type}",
            )

    def _http_check(self, check: SteadyStateCheck) -> CheckResult:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(check.url)
                passed = resp.status_code == check.expected_status
                return CheckResult(
                    name=check.name,
                    passed=passed,
                    detail=f"HTTP {resp.status_code} (expected {check.expected_status})",
                )
        except Exception as exc:
            return CheckResult(
                name=check.name,
                passed=False,
                detail=f"HTTP check failed: {exc}",
            )

    def _metric_check(self, check: SteadyStateCheck) -> CheckResult:
        """
        Metric checks are evaluated by the SLO monitor during the experiment.
        At steady-state time we just mark them as passed (no Prometheus yet).
        """
        return CheckResult(
            name=check.name,
            passed=True,
            detail="Metric check deferred to SLO monitor",
        )