"""
Experiment model — loads and validates a YAML experiment config.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import yaml


class ExperimentVerdict(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ABORTED = "aborted"
    RUNNING = "running"
    PENDING = "pending"


@dataclass
class SteadyStateCheck:
    name: str
    check_type: str        # "http" or "metric"
    url: str | None = None
    expected_status: int = 200
    metric: str | None = None
    threshold: float | None = None
    operator: str = "<"    # "<", ">", "<=", ">="


@dataclass
class SLOConfig:
    error_rate_percent: float = 5.0
    latency_p99_ms: float = 500.0
    availability_percent: float = 95.0


@dataclass
class FaultConfig:
    fault_type: str
    target: str
    duration_seconds: int
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackConfig:
    on_slo_breach: bool = True
    grace_period_seconds: int = 10


@dataclass
class ObservabilityConfig:
    prometheus_url: str = "http://localhost:9090"
    scrape_interval_seconds: int = 5
    metrics: list[str] = field(default_factory=list)


@dataclass
class Experiment:
    name: str
    description: str
    version: str
    steady_state_checks: list[SteadyStateCheck]
    fault: FaultConfig
    slo: SLOConfig
    rollback: RollbackConfig
    observability: ObservabilityConfig
    verdict: ExperimentVerdict = ExperimentVerdict.PENDING
    experiment_id: str | None = None

    @classmethod
    def from_yaml(cls, path: str) -> "Experiment":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Experiment":
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Experiment":
        # Parse steady state checks
        checks = []
        for c in data.get("steady_state", {}).get("checks", []):
            checks.append(SteadyStateCheck(
                name=c["name"],
                check_type=c["type"],
                url=c.get("url"),
                expected_status=c.get("expected_status", 200),
                metric=c.get("metric"),
                threshold=c.get("threshold"),
                operator=c.get("operator", "<"),
            ))

        # Parse fault config
        fault_data = data["fault"]
        fault = FaultConfig(
            fault_type=fault_data["type"],
            target=fault_data["target"],
            duration_seconds=fault_data["duration_seconds"],
            params=fault_data.get("params", {}),
        )

        # Parse SLO
        slo_data = data.get("slo", {})
        slo = SLOConfig(
            error_rate_percent=slo_data.get("error_rate_percent", 5.0),
            latency_p99_ms=slo_data.get("latency_p99_ms", 500.0),
            availability_percent=slo_data.get("availability_percent", 95.0),
        )

        # Parse rollback
        rb_data = data.get("rollback", {})
        rollback = RollbackConfig(
            on_slo_breach=rb_data.get("on_slo_breach", True),
            grace_period_seconds=rb_data.get("grace_period_seconds", 10),
        )

        # Parse observability
        obs_data = data.get("observability", {})
        observability = ObservabilityConfig(
            prometheus_url=obs_data.get("prometheus_url", "http://localhost:9090"),
            scrape_interval_seconds=obs_data.get("scrape_interval_seconds", 5),
            metrics=obs_data.get("metrics", []),
        )

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            steady_state_checks=checks,
            fault=fault,
            slo=slo,
            rollback=rollback,
            observability=observability,
        )