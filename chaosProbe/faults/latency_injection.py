"""
Latency Injection Fault
Adds artificial delay to HTTP responses on a target service.
"""
from __future__ import annotations

import subprocess
import httpx
from typing import Any

from chaosProbe.faults.base import BaseFault, FaultResult, FaultState
from chaosProbe.utils.logger import get_logger

logger = get_logger(__name__)


class LatencyInjectionFault(BaseFault):
    fault_type = "latency_injection"

    def __init__(
        self,
        target: str,
        duration_seconds: int,
        latency_ms: int = 200,
        jitter_ms: int = 50,
        target_url: str | None = None,
        network_interface: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(target, duration_seconds, **kwargs)
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms
        self.target_url = target_url
        self.network_interface = network_interface

    def inject(self) -> FaultResult:
        logger.info(
            f"[latency_injection] Injecting {self.latency_ms}ms "
            f"on {self.target} for {self.duration_seconds}s"
        )
        self._result.state = FaultState.INJECTING
        try:
            if self.target_url:
                self._inject_via_http()
            elif self.network_interface:
                self._inject_via_tc()
            else:
                raise ValueError(
                    "Either target_url or network_interface must be provided"
                )
            self._result.state = FaultState.ACTIVE
            self._result.metadata = {
                "latency_ms": self.latency_ms,
                "jitter_ms": self.jitter_ms,
                "method": "http" if self.target_url else "tc",
            }
            logger.info(f"[latency_injection] Active — {self.latency_ms}ms injected")
        except Exception as exc:
            self._mark_failed(str(exc))
            logger.error(f"[latency_injection] Injection failed: {exc}")
        return self._result

    def recover(self) -> FaultResult:
        self._result.state = FaultState.RECOVERING
        try:
            if self.target_url:
                self._recover_via_http()
            elif self.network_interface:
                self._recover_via_tc()
            self._mark_recovered()
            logger.info("[latency_injection] Recovered — latency removed")
        except Exception as exc:
            self._mark_failed(str(exc))
            logger.error(f"[latency_injection] Recovery failed: {exc}")
        return self._result

    def _inject_via_http(self) -> None:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                f"{self.target_url}/chaos/inject-latency",
                params={"latency_ms": self.latency_ms},
            )
            resp.raise_for_status()

    def _recover_via_http(self) -> None:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(f"{self.target_url}/chaos/reset")
            resp.raise_for_status()

    def _inject_via_tc(self) -> None:
        iface = self.network_interface
        subprocess.run(
            [
                "tc", "qdisc", "add", "dev", iface, "root", "netem",
                "delay", f"{self.latency_ms}ms", f"{self.jitter_ms}ms",
            ],
            check=True,
        )

    def _recover_via_tc(self) -> None:
        subprocess.run(
            ["tc", "qdisc", "del", "dev", self.network_interface, "root"],
            check=True,
        )