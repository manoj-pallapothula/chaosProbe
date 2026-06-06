"""Tests for LatencyInjectionFault."""
from unittest.mock import patch, MagicMock
import httpx
import pytest

from chaosProbe.faults.latency_injection import LatencyInjectionFault
from chaosProbe.faults.base import FaultState


class TestLatencyInjectionFault:
    def _make_http_fault(self, **kwargs):
        defaults = dict(
            target="target-api",
            duration_seconds=30,
            latency_ms=200,
            jitter_ms=50,
            target_url="http://localhost:8081",
        )
        defaults.update(kwargs)
        return LatencyInjectionFault(**defaults)

    def _make_tc_fault(self, **kwargs):
        defaults = dict(
            target="eth0-interface",
            duration_seconds=30,
            latency_ms=100,
            jitter_ms=10,
            network_interface="eth0",
        )
        defaults.update(kwargs)
        return LatencyInjectionFault(**defaults)

    def test_inject_via_http_success(self):
        fault = self._make_http_fault()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = fault.inject()

        assert result.state == FaultState.ACTIVE
        assert result.metadata["latency_ms"] == 200
        assert result.metadata["method"] == "http"

    def test_inject_via_tc_success(self):
        fault = self._make_tc_fault()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = fault.inject()

        assert result.state == FaultState.ACTIVE
        assert result.metadata["method"] == "tc"

    def test_inject_no_target_raises(self):
        fault = LatencyInjectionFault(
            target="nowhere",
            duration_seconds=10,
            latency_ms=100,
        )
        result = fault.inject()
        assert result.state == FaultState.FAILED
        assert "target_url or network_interface" in result.error

    def test_recover_via_http(self):
        fault = self._make_http_fault()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            fault.inject()
            result = fault.recover()

        assert result.state == FaultState.RECOVERED

    def test_recover_via_tc(self):
        fault = self._make_tc_fault()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            fault.inject()
            result = fault.recover()

        assert result.state == FaultState.RECOVERED

    def test_http_failure_marks_failed(self):
        fault = self._make_http_fault()
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("connection refused")
            mock_client_cls.return_value = mock_client

            result = fault.inject()

        assert result.state == FaultState.FAILED