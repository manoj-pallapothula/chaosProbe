"""Tests for Orchestrator."""
from unittest.mock import patch, MagicMock
import pytest

from chaosProbe.engine.orchestrator import Orchestrator, ExperimentRun
from chaosProbe.engine.experiment import (
    Experiment, ExperimentVerdict, FaultConfig,
    SLOConfig, RollbackConfig, ObservabilityConfig, SteadyStateCheck,
)
from chaosProbe.faults.base import FaultState


def _make_experiment(**kwargs) -> Experiment:
    defaults = dict(
        name="Test Experiment",
        description="A test",
        version="1.0",
        steady_state_checks=[
            SteadyStateCheck(
                name="health",
                check_type="metric",
            )
        ],
        fault=FaultConfig(
            fault_type="cpu_stress",
            target="test-service",
            duration_seconds=1,
            params={"cpu_load_percent": 50},
        ),
        slo=SLOConfig(),
        rollback=RollbackConfig(on_slo_breach=True, grace_period_seconds=0),
        observability=ObservabilityConfig(scrape_interval_seconds=1),
    )
    defaults.update(kwargs)
    return Experiment(**defaults)


class TestOrchestrator:
    def test_run_passes_when_healthy(self):
        orchestrator = Orchestrator()
        experiment = _make_experiment()

        mock_fault = MagicMock()
        mock_fault.inject.return_value = MagicMock(
            state=FaultState.ACTIVE,
            to_dict=lambda: {"state": "active"},
        )
        mock_fault.recover.return_value = MagicMock(state=FaultState.RECOVERED)

        with patch("chaosProbe.engine.orchestrator.FAULT_REGISTRY", {"cpu_stress": lambda **k: mock_fault}):
            run = orchestrator.run(experiment)

        assert run.verdict == ExperimentVerdict.PASSED
        assert run.ended_at is not None
        assert run.experiment_id is not None

    def test_run_aborts_when_pre_checks_fail(self):
        orchestrator = Orchestrator()
        experiment = _make_experiment(
            steady_state_checks=[
                SteadyStateCheck(
                    name="failing check",
                    check_type="http",
                    url="http://localhost:9999/health",
                    expected_status=200,
                )
            ]
        )

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = Exception("connection refused")
            mock_client_cls.return_value = mock_client

            run = orchestrator.run(experiment)

        assert run.verdict == ExperimentVerdict.ABORTED
        assert "steady-state" in run.abort_reason.lower()

    def test_run_fails_on_slo_breach(self):
        mock_slo_monitor = MagicMock()
        mock_slo_monitor.check.return_value = True

        orchestrator = Orchestrator(slo_monitor=mock_slo_monitor)
        experiment = _make_experiment()

        mock_fault = MagicMock()
        mock_fault.inject.return_value = MagicMock(
            state=FaultState.ACTIVE,
            to_dict=lambda: {"state": "active"},
        )
        mock_fault.recover.return_value = MagicMock(state=FaultState.RECOVERED)

        with patch("chaosProbe.engine.orchestrator.FAULT_REGISTRY", {"cpu_stress": lambda **k: mock_fault}):
            run = orchestrator.run(experiment)

        assert run.slo_breached is True
        assert run.verdict == ExperimentVerdict.FAILED

    def test_run_aborts_on_unknown_fault(self):
        orchestrator = Orchestrator()
        experiment = _make_experiment(
            fault=FaultConfig(
                fault_type="unknown_fault_type",
                target="test-service",
                duration_seconds=1,
            )
        )
        run = orchestrator.run(experiment)
        assert run.verdict == ExperimentVerdict.ABORTED

    def test_timeline_events_recorded(self):
        orchestrator = Orchestrator()
        experiment = _make_experiment()

        mock_fault = MagicMock()
        mock_fault.inject.return_value = MagicMock(
            state=FaultState.ACTIVE,
            to_dict=lambda: {"state": "active"},
        )
        mock_fault.recover.return_value = MagicMock(state=FaultState.RECOVERED)

        with patch("chaosProbe.engine.orchestrator.FAULT_REGISTRY", {"cpu_stress": lambda **k: mock_fault}):
            run = orchestrator.run(experiment)

        events = [e["event"] for e in run.timeline]
        assert "experiment_started" in events
        assert "fault_active" in events
        assert "experiment_completed" in events

    def test_run_to_dict(self):
        orchestrator = Orchestrator()
        experiment = _make_experiment()

        mock_fault = MagicMock()
        mock_fault.inject.return_value = MagicMock(
            state=FaultState.ACTIVE,
            to_dict=lambda: {"state": "active"},
        )
        mock_fault.recover.return_value = MagicMock(state=FaultState.RECOVERED)

        with patch("chaosProbe.engine.orchestrator.FAULT_REGISTRY", {"cpu_stress": lambda **k: mock_fault}):
            run = orchestrator.run(experiment)

        result = run.to_dict()
        assert "experiment_id" in result
        assert "verdict" in result
        assert "timeline" in result