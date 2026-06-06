"""Tests for HypothesisChecker."""
from unittest.mock import patch, MagicMock
import httpx
import pytest

from chaosProbe.engine.hypothesis import HypothesisChecker, CheckResult
from chaosProbe.engine.experiment import SteadyStateCheck


class TestHypothesisChecker:
    def _make_checker(self):
        return HypothesisChecker(timeout=2.0)

    def _make_http_check(self, **kwargs):
        defaults = dict(
            name="API health",
            check_type="http",
            url="http://localhost:8081/health",
            expected_status=200,
        )
        defaults.update(kwargs)
        return SteadyStateCheck(**defaults)

    def _make_metric_check(self, **kwargs):
        defaults = dict(
            name="Error rate",
            check_type="metric",
            metric="target_error_rate",
            threshold=0.01,
            operator="<",
        )
        defaults.update(kwargs)
        return SteadyStateCheck(**defaults)

    def test_http_check_passes(self):
        checker = self._make_checker()
        check = self._make_http_check()
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = checker._http_check(check)

        assert result.passed is True
        assert "200" in result.detail

    def test_http_check_fails_wrong_status(self):
        checker = self._make_checker()
        check = self._make_http_check(expected_status=200)
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = checker._http_check(check)

        assert result.passed is False

    def test_http_check_fails_on_exception(self):
        checker = self._make_checker()
        check = self._make_http_check()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError("refused")
            mock_client_cls.return_value = mock_client

            result = checker._http_check(check)

        assert result.passed is False
        assert "failed" in result.detail

    def test_metric_check_always_passes(self):
        checker = self._make_checker()
        check = self._make_metric_check()
        result = checker._metric_check(check)
        assert result.passed is True

    def test_unknown_check_type_fails(self):
        checker = self._make_checker()
        check = SteadyStateCheck(name="bad", check_type="unknown")
        result = checker._run_check(check)
        assert result.passed is False
        assert "Unknown check type" in result.detail

    def test_run_all_returns_all_results(self):
        checker = self._make_checker()
        checks = [
            self._make_metric_check(name="check1"),
            self._make_metric_check(name="check2"),
        ]
        results = checker.run_all(checks)
        assert len(results) == 2

    def test_all_passed_true(self):
        checker = self._make_checker()
        results = [
            CheckResult(name="a", passed=True, detail="ok"),
            CheckResult(name="b", passed=True, detail="ok"),
        ]
        assert checker.all_passed(results) is True

    def test_all_passed_false(self):
        checker = self._make_checker()
        results = [
            CheckResult(name="a", passed=True, detail="ok"),
            CheckResult(name="b", passed=False, detail="failed"),
        ]
        assert checker.all_passed(results) is False