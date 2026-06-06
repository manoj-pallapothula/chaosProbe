"""Tests for MemoryPressureFault."""
import time
from unittest.mock import patch, MagicMock

import pytest

from chaosProbe.faults.memory_pressure import MemoryPressureFault
from chaosProbe.faults.base import FaultState


class TestMemoryPressureFault:
    def _make_fault(self, **kwargs):
        defaults = dict(target="test-service", duration_seconds=2, memory_mb=16)
        defaults.update(kwargs)
        return MemoryPressureFault(**defaults)

    def test_init_stores_params(self):
        fault = self._make_fault(memory_mb=512)
        assert fault.memory_mb == 512
        assert fault.duration_seconds == 2

    def test_inject_starts_thread(self):
        fault = self._make_fault(memory_mb=1)
        with patch.object(fault, "_hold_memory"):
            result = fault.inject()
            time.sleep(0.2)

        assert result.state == FaultState.ACTIVE
        assert result.metadata["memory_mb"] == 1
        assert result.metadata["memory_bytes"] == 1 * 1024 * 1024

    def test_inject_failure(self):
        fault = self._make_fault()
        with patch("threading.Thread") as mock_thread:
            mock_thread.side_effect = RuntimeError("thread failed")
            result = fault.inject()

        assert result.state == FaultState.FAILED
        assert "thread failed" in result.error

    def test_recover_stops_thread(self):
        fault = self._make_fault(memory_mb=1, duration_seconds=30)
        with patch.object(fault, "_hold_memory"):
            fault.inject()

        result = fault.recover()
        assert result.state == FaultState.RECOVERED
        assert fault._stop_event.is_set()

    def test_recover_before_inject(self):
        fault = self._make_fault()
        result = fault.recover()
        assert result.state in (FaultState.RECOVERED, FaultState.FAILED)

    def test_fault_type(self):
        assert MemoryPressureFault.fault_type == "memory_pressure"