"""
Pydantic models for API request/response schemas.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class SteadyStateCheckSchema(BaseModel):
    name: str
    type: str
    url: str | None = None
    expected_status: int = 200
    metric: str | None = None
    threshold: float | None = None
    operator: str = "<"


class FaultConfigSchema(BaseModel):
    type: str
    target: str
    duration_seconds: int
    params: dict[str, Any] = {}


class SLOConfigSchema(BaseModel):
    error_rate_percent: float = 5.0
    latency_p99_ms: float = 500.0
    availability_percent: float = 95.0


class RollbackConfigSchema(BaseModel):
    on_slo_breach: bool = True
    grace_period_seconds: int = 10


class ObservabilityConfigSchema(BaseModel):
    prometheus_url: str = "http://localhost:9090"
    scrape_interval_seconds: int = 5
    metrics: list[str] = []


class ExperimentRequest(BaseModel):
    name: str
    description: str = ""
    version: str = "1.0"
    steady_state: dict[str, Any] = {"checks": []}
    fault: FaultConfigSchema
    slo: SLOConfigSchema = SLOConfigSchema()
    rollback: RollbackConfigSchema = RollbackConfigSchema()
    observability: ObservabilityConfigSchema = ObservabilityConfigSchema()


class CheckResultSchema(BaseModel):
    name: str
    passed: bool
    detail: str


class ExperimentRunResponse(BaseModel):
    experiment_id: str
    experiment_name: str
    started_at: float
    ended_at: float | None
    duration_seconds: float | None
    verdict: str
    slo_breached: bool
    abort_reason: str | None
    pre_checks: list[dict[str, Any]]
    post_checks: list[dict[str, Any]]
    fault_result: dict[str, Any] | None
    timeline: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    environment: str = "development"