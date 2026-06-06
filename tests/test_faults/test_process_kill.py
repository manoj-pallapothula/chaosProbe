"""Tests for ProcessKillFault."""
import signal
from unittest.mock import patch, MagicMock
import pytest
import psutil

from chaosProbe.faults.process_kill import ProcessKillFault
from chaosProbe.faults.base import FaultState


class TestProcessKillFault:
    def test_kill_by_name_success(self):
        fault = ProcessKillFault(
            target="test-service",
            duration_seconds=5,
            process_name="python",
        )
        mock_proc = MagicMock()
        mock_proc.info = {"pid": 1234, "name": "python3", "cmdline": ["python3", "app.py"]}
        mock_proc.pid = 1234

        with patch("psutil.process_iter", return_value=[mock_proc]):
            result = fault.inject()

        assert result.state == FaultState.ACTIVE
        assert 1234 in result.metadata["killed_pids"]
        mock_proc.send_signal.assert_called_once_with(signal.SIGKILL)

    def test_kill_by_name_not_found(self):
        fault = ProcessKillFault(
            target="test-service",
            duration_seconds=5,
            process_name="nonexistent_xyz",
        )
        with patch("psutil.process_iter", return_value=[]):
            result = fault.inject()

        assert result.state == FaultState.FAILED
        assert "No process matching" in result.error

    def test_kill_by_pid_success(self):
        fault = ProcessKillFault(
            target="test-service",
            duration_seconds=5,
            pid=9999,
            signal_type="SIGTERM",
        )
        mock_proc = MagicMock()
        with patch("psutil.Process", return_value=mock_proc):
            result = fault.inject()

        assert result.state == FaultState.ACTIVE
        mock_proc.send_signal.assert_called_once_with(signal.SIGTERM)

    def test_kill_by_pid_not_found(self):
        fault = ProcessKillFault(
            target="test-service",
            duration_seconds=5,
            pid=99999999,
        )
        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(99999999)):
            result = fault.inject()

        assert result.state == FaultState.FAILED

    def test_kill_container_success(self):
        fault = ProcessKillFault(
            target="test-service",
            duration_seconds=5,
            container_name="target-api",
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = fault.inject()

        assert result.state == FaultState.ACTIVE
        assert result.metadata["container_killed"] == "target-api"

    def test_kill_container_failure(self):
        fault = ProcessKillFault(
            target="test-service",
            duration_seconds=5,
            container_name="nonexistent-container",
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stderr="No such container"
            )
            result = fault.inject()

        assert result.state == FaultState.FAILED

    def test_no_target_raises(self):
        fault = ProcessKillFault(target="test-service", duration_seconds=5)
        result = fault.inject()
        assert result.state == FaultState.FAILED
        assert "Must specify" in result.error

    def test_recover_completes(self):
        fault = ProcessKillFault(
            target="test-service",
            duration_seconds=0,
            pid=1234,
        )
        mock_proc = MagicMock()
        with patch("psutil.Process", return_value=mock_proc):
            fault.inject()
        result = fault.recover()
        assert result.state == FaultState.RECOVERED