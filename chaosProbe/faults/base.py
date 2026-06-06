"""
Base fault interface.
Every fault injector inherits from BaseFault and implements:
  - inject()   → start the failure
  - recover()  → undo the failure
  - status()   → current state as a dict
"""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FaultState(str, Enum):
    IDLE = "idle"
    INJECTING = "injecting"
    ACTIVE = "active"
    RECOVERING = "recovering"
    RECOVERED = "recovered"
    FAILED = "failed"


@dataclass
class FaultResult:
    fault_type: str
    target: str
    state: FaultState
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fault_type": self.fault_type,
            "target": self.target,
            "state": self.state.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": (
                (self.ended_at - self.started_at) if self.ended_at else None
            ),
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseFault(abc.ABC):
    """Abstract base for all fault injectors."""

    fault_type: str = "base"

    def __init__(self, target: str, duration_seconds: int, **kwargs: Any):
        self.target = target
        self.duration_seconds = duration_seconds
        self.kwargs = kwargs
        self._result = FaultResult(
            fault_type=self.fault_type,
            target=target,
            state=FaultState.IDLE,
        )

    @abc.abstractmethod
    def inject(self) -> FaultResult:
        """Start injecting the fault."""

    @abc.abstractmethod
    def recover(self) -> FaultResult:
        """Undo the fault and restore normal operation."""

    def status(self) -> dict[str, Any]:
        return self._result.to_dict()

    def _mark_active(self) -> None:
        self._result.state = FaultState.ACTIVE

    def _mark_recovered(self) -> None:
        self._result.state = FaultState.RECOVERED
        self._result.ended_at = time.time()

    def _mark_failed(self, error: str) -> None:
        self._result.state = FaultState.FAILED
        self._result.error = error
        self._result.ended_at = time.time()