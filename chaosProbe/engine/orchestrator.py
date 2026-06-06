"""
Experiment Orchestrator — the brain of ChaosProbe.
Runs the full experiment lifecycle:
  1. Load experiment
  2. Check steady-state hypothesis
  3. Inject fault
  4. Monitor SLOs
  5. Rollback if breached
  6. Recover
  7. Re-check steady-state
  8. Return verdict
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from chaosProbe.engine.experiment import Experiment, ExperimentVerdict
from chaosProbe.engine.hypothesis import HypothesisChecker, CheckResult
from chaosProbe.faults import FAULT_REGISTRY
from chaosProbe.faults.base import BaseFault, FaultResult
from chaosProbe.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExperimentRun:
    experiment_id: str
    experiment_name: str
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None
    verdict: ExperimentVerdict = ExperimentVerdict.PENDING
    pre_checks: list[CheckResult] = field(default_factory=list)
    post_checks: list[CheckResult] = field(default_factory=list)
    fault_result: FaultResult | None = None
    slo_breached: bool = False
    abort_reason: str | None = None
    timeline: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "experiment_name": self.experiment_name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": (
                (self.ended_at - self.started_at) if self.ended_at else None
            ),
            "verdict": self.verdict.value,
            "pre_checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail}
                for c in self.pre_checks
            ],
            "post_checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail}
                for c in self.post_checks
            ],
            "fault_result": self.fault_result.to_dict() if self.fault_result else None,
            "slo_breached": self.slo_breached,
            "abort_reason": self.abort_reason,
            "timeline": self.timeline,
        }


class Orchestrator:
    """Runs a full chaos experiment end to end."""

    def __init__(self, slo_monitor=None):
        self.checker = HypothesisChecker()
        self.slo_monitor = slo_monitor

    def run(self, experiment: Experiment) -> ExperimentRun:
        run = ExperimentRun(
            experiment_id=str(uuid.uuid4()),
            experiment_name=experiment.name,
        )
        experiment.experiment_id = run.experiment_id

        logger.info(f"[orchestrator] Starting experiment: {experiment.name}")
        self._log_event(run, "experiment_started", {"name": experiment.name})

        # ── Step 1: Pre-experiment steady-state check ─────────────────────────
        logger.info("[orchestrator] Running pre-experiment steady-state checks")
        run.pre_checks = self.checker.run_all(experiment.steady_state_checks)

        if not self.checker.all_passed(run.pre_checks):
            run.verdict = ExperimentVerdict.ABORTED
            run.abort_reason = "Pre-experiment steady-state checks failed"
            run.ended_at = time.time()
            self._log_event(run, "aborted", {"reason": run.abort_reason})
            logger.warning(f"[orchestrator] Aborted: {run.abort_reason}")
            return run

        self._log_event(run, "steady_state_confirmed", {})

        # ── Step 2: Build and inject fault ───────────────────────────────────
        fault = self._build_fault(experiment)
        if fault is None:
            run.verdict = ExperimentVerdict.ABORTED
            run.abort_reason = f"Unknown fault type: {experiment.fault.fault_type}"
            run.ended_at = time.time()
            return run

        logger.info(f"[orchestrator] Injecting fault: {experiment.fault.fault_type}")
        self._log_event(run, "fault_injection_started", {
            "fault_type": experiment.fault.fault_type,
            "target": experiment.fault.target,
        })

        fault_result = fault.inject()
        run.fault_result = fault_result
        self._log_event(run, "fault_active", fault_result.to_dict())

        # ── Step 3: Monitor during experiment ────────────────────────────────
        slo_breached = self._monitor(experiment, fault, run)

        # ── Step 4: Recover ───────────────────────────────────────────────────
        logger.info("[orchestrator] Recovering fault")
        fault.recover()
        self._log_event(run, "fault_recovered", {})

        # ── Step 5: Post-experiment steady-state check ────────────────────────
        logger.info("[orchestrator] Running post-experiment steady-state checks")
        run.post_checks = self.checker.run_all(experiment.steady_state_checks)
        self._log_event(run, "post_steady_state_checked", {})

        # ── Step 6: Verdict ───────────────────────────────────────────────────
        if run.slo_breached:
            run.verdict = ExperimentVerdict.FAILED
        elif not self.checker.all_passed(run.post_checks):
            run.verdict = ExperimentVerdict.FAILED
        else:
            run.verdict = ExperimentVerdict.PASSED

        run.ended_at = time.time()
        self._log_event(run, "experiment_completed", {"verdict": run.verdict.value})
        logger.info(f"[orchestrator] Experiment complete — verdict: {run.verdict.value.upper()}")

        return run

    def _build_fault(self, experiment: Experiment) -> BaseFault | None:
        fault_cls = FAULT_REGISTRY.get(experiment.fault.fault_type)
        if not fault_cls:
            return None
        return fault_cls(
            target=experiment.fault.target,
            duration_seconds=experiment.fault.duration_seconds,
            **experiment.fault.params,
        )

    def _monitor(self, experiment: Experiment, fault: BaseFault, run: ExperimentRun) -> bool:
        """
        Monitor the experiment for its duration.
        Checks SLOs every scrape_interval seconds.
        Triggers rollback if SLO is breached.
        """
        duration = experiment.fault.duration_seconds
        interval = experiment.observability.scrape_interval_seconds
        deadline = time.time() + duration
        slo_breached = False

        while time.time() < deadline:
            time.sleep(min(interval, deadline - time.time()))

            if self.slo_monitor:
                breach = self.slo_monitor.check(experiment.slo)
                if breach:
                    logger.warning("[orchestrator] SLO breach detected!")
                    run.slo_breached = True
                    slo_breached = True

                    if experiment.rollback.on_slo_breach:
                        grace = experiment.rollback.grace_period_seconds
                        logger.warning(
                            f"[orchestrator] Rolling back after {grace}s grace period"
                        )
                        time.sleep(grace)
                        self._log_event(run, "slo_breach_rollback", {})
                        break

        return slo_breached

    def _log_event(self, run: ExperimentRun, event: str, data: dict[str, Any]) -> None:
        run.timeline.append({
            "timestamp": time.time(),
            "event": event,
            "data": data,
        })