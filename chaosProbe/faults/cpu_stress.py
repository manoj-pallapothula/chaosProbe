"""
CPU Stress Fault
Uses stress-ng (if available) or a pure-Python CPU burner.
Spawns worker processes that peg CPUs at the specified load percentage.
"""
from __future__ import annotations

import subprocess
import signal
import os
from typing import Any

from chaosProbe.faults.base import BaseFault, FaultResult, FaultState
from chaosProbe.utils.logger import get_logger

logger = get_logger(__name__)


class CpuStressFault(BaseFault):
    fault_type = "cpu_stress"

    def __init__(
        self,
        target: str,
        duration_seconds: int,
        cpu_load_percent: int = 80,
        workers: int = 2,
        **kwargs: Any,
    ):
        super().__init__(target, duration_seconds, **kwargs)
        self.cpu_load_percent = min(100, max(1, cpu_load_percent))
        self.workers = workers
        self._process: subprocess.Popen | None = None

    def inject(self) -> FaultResult:
        logger.info(
            f"[cpu_stress] Injecting {self.cpu_load_percent}% CPU load "
            f"on {self.target} for {self.duration_seconds}s"
        )
        self._result.state = FaultState.INJECTING
        try:
            self._process = self._start_stress()
            self._result.state = FaultState.ACTIVE
            self._result.metadata = {
                "cpu_load_percent": self.cpu_load_percent,
                "workers": self.workers,
                "pid": self._process.pid,
            }
            logger.info(f"[cpu_stress] Active — PID {self._process.pid}")
        except Exception as exc:
            self._mark_failed(str(exc))
            logger.error(f"[cpu_stress] Injection failed: {exc}")
        return self._result

    def recover(self) -> FaultResult:
        self._result.state = FaultState.RECOVERING
        try:
            if self._process and self._process.poll() is None:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                self._process.wait(timeout=5)
            self._mark_recovered()
            logger.info("[cpu_stress] Recovered")
        except ProcessLookupError:
            self._mark_recovered()
        except Exception as exc:
            self._mark_failed(str(exc))
            logger.error(f"[cpu_stress] Recovery failed: {exc}")
        return self._result

    def _start_stress(self) -> subprocess.Popen:
        try:
            return subprocess.Popen(
                [
                    "stress-ng",
                    "--cpu", str(self.workers),
                    "--cpu-load", str(self.cpu_load_percent),
                    "--timeout", str(self.duration_seconds),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
        except FileNotFoundError:
            logger.warning("[cpu_stress] stress-ng not found, using Python burner")
            return self._python_burner()

    def _python_burner(self) -> subprocess.Popen:
        script = (
            "import time, math; "
            f"end = time.time() + {self.duration_seconds}; "
            "[math.factorial(10000) for _ in iter(int, 1) if time.time() < end]"
        )
        return subprocess.Popen(
            ["python3", "-c", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )