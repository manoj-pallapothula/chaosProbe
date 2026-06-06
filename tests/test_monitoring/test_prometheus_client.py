"""Tests for PrometheusClient."""
from unittest.mock import patch, MagicMock
import pytest

from chaosProbe.monitoring.prometheus_client import PrometheusClient


class TestPrometheusClient:
    def _make_client(self):
        return PrometheusClient(base_url="http://localhost:9090", timeout=2.0)

    def _mock_response(self, value: float):
        return {
            "data": {
                "result": [
                    {"value": [1234567890, str(value)]}
                ]
            }
        }

    def test_query_returns_float(self):
        client = self._make_client()
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.json.return_value = self._mock_response(3.14)
            mock_resp.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value = mock_client

            result = client.query("up")

        assert result == pytest.approx(3.14)

    def test_query_returns_none_on_empty(self):
        client = self._make_client()
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"result": []}}
            mock_resp.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value = mock_client

            result = client.query("up")

        assert result is None

    def test_query_returns_none_on_exception(self):
        client = self._make_client()
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = Exception("connection refused")
            mock_cls.return_value = mock_client

            result = client.query("up")

        assert result is None

    def test_query_range_returns_tuples(self):
        client = self._make_client()
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "data": {
                    "result": [
                        {"values": [[1000.0, "1.5"], [2000.0, "2.5"]]}
                    ]
                }
            }
            mock_resp.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value = mock_client

            result = client.query_range("up", 1000.0, 2000.0)

        assert result == [(1000.0, 1.5), (2000.0, 2.5)]

    def test_query_range_returns_empty_on_error(self):
        client = self._make_client()
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = Exception("timeout")
            mock_cls.return_value = mock_client

            result = client.query_range("up", 1000.0, 2000.0)

        assert result == []

    def test_is_healthy_true(self):
        client = self._make_client()
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client.get.return_value = mock_resp
            mock_cls.return_value = mock_client

            assert client.is_healthy() is True

    def test_is_healthy_false_on_exception(self):
        client = self._make_client()
        with patch("httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = Exception("refused")
            mock_cls.return_value = mock_client

            assert client.is_healthy() is False