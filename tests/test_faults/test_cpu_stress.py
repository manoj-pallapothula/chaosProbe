"""Tests for CpuStressFault."""
import signal
from unittest.mock import patch, MagicMock

import pytest

from chaosProbe.faults.cpu_stress import CpuStressFault
from chaosProbe.faults.base import FaultState


class TestCpuStressFault:
    def _make_fault(self, **kwargs):
        defaults = dict(target="test-service", duration_seconds=5, cpu_load_percent=50)
        defaults.update(kwargs)
        return CpuStressFault(**defaults)

    def test_init_clamps_cpu_load(self):
        fault = self._make_fault(cpu_load_percent=150)
        assert fault.cpu_load_percent == 100

        fault = self._make_fault(cpu_load_percent=-10)
        assert fault.cpu_load_percent == 1

    def test_inject_success(self):
        fault = self._make_fault()
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None

        with patch.object(fault, "_start_stress", return_value=mock_proc):
            result = fault.inject()

        assert result.state == FaultState.ACTIVE
        assert result.metadata["cpu_load_percent"] == 50
        assert result.metadata["pid"] == 12345
        assert result.error is None

    def test_inject_failure_marks_state(self):
        fault = self._make_fault()
        with patch.object(fault, "_start_stress", side_effect=OSError("no stress-ng")):
            result = fault.inject()

        assert result.state == FaultState.FAILED
        assert "no stress-ng" in result.error

    def test_recover_terminates_process(self):
        fault = self._make_fault()
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None

        with patch.object(fault, "_start_stress", return_value=mock_proc):
            fault.inject()

        with patch("os.killpg") as mock_kill, patch("os.getpgid", return_value=12345):
            result = fault.recover()

        assert result.state == FaultState.RECOVERED
        mock_kill.assert_called_once_with(12345, signal.SIGTERM)

    def test_recover_handles_dead_process(self):
        fault = self._make_fault()
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_proc.poll.return_value = None

        with patch.object(fault, "_start_stress", return_value=mock_proc):
            fault.inject()

        with patch("os.killpg", side_effect=ProcessLookupError), \
             patch("os.getpgid", return_value=99999):
            result = fault.recover()

        assert result.state == FaultState.RECOVERED

    def test_status_returns_dict(self):
        fault = self._make_fault()
        status = fault.status()
        assert status["fault_type"] == "cpu_stress"
        assert status["target"] == "test-service"
        assert "state" in status

    def test_python_burner_fallback(self):
        fault = self._make_fault(duration_seconds=1)
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = [
                FileNotFoundError("stress-ng not found"),
                MagicMock(pid=222),
            ]
            proc = fault._start_stress()
            assert proc is not None