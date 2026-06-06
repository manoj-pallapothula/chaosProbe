"""
Process Kill Fault
Kills a target process by name, PID, or Docker container name.
"""
from __future__ import annotations

import signal
import subprocess
import time
from typing import Any

import psutil

from chaosProbe.faults.base import BaseFault, FaultResult, FaultState
from chaosProbe.utils.logger import get_logger

logger = get_logger(__name__)


class ProcessKillFault(BaseFault):
    fault_type = "process_kill"

    def __init__(
        self,
        target: str,
        duration_seconds: int,
        process_name: str | None = None,
        pid: int | None = None,
        container_name: str | None = None,
        signal_type: str = "SIGKILL",
        **kwargs: Any,
    ):
        super().__init__(target, duration_seconds, **kwargs)
        self.process_name = process_name
        self.pid = pid
        self.container_name = container_name
        self.signal_type = signal_type
        self._killed_pids: list[int] = []

    def inject(self) -> FaultResult:
        logger.info(
            f"[process_kill] Sending {self.signal_type} to {self.target}"
        )
        self._result.state = FaultState.INJECTING
        try:
            if self.container_name:
                self._kill_container()
            elif self.process_name:
                self._kill_by_name()
            elif self.pid:
                self._kill_by_pid(self.pid)
            else:
                raise ValueError(
                    "Must specify process_name, pid, or container_name"
                )
            self._result.state = FaultState.ACTIVE
            self._result.metadata = {
                "signal": self.signal_type,
                "killed_pids": self._killed_pids,
                "container": self.container_name,
                "container_killed": self.container_name if self.container_name else None,
            }
            logger.info(f"[process_kill] Killed PIDs: {self._killed_pids}")
        except Exception as exc:
            self._mark_failed(str(exc))
            logger.error(f"[process_kill] Injection failed: {exc}")
        return self._result

    def recover(self) -> FaultResult:
        self._result.state = FaultState.RECOVERING
        if self.container_name:
            logger.info(
                f"[process_kill] Waiting for container {self.container_name} to restart"
            )
            time.sleep(min(self.duration_seconds, 30))
        self._mark_recovered()
        logger.info("[process_kill] Recovery complete")
        return self._result

    def _kill_by_name(self) -> None:
        sig = getattr(signal, self.signal_type, signal.SIGKILL)
        found = False
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = proc.info["name"] or ""
                cmdline = " ".join(proc.info["cmdline"] or [])
                if self.process_name in name or self.process_name in cmdline:
                    proc.send_signal(sig)
                    self._killed_pids.append(proc.pid)
                    found = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if not found:
            raise RuntimeError(f"No process matching '{self.process_name}' found")

    def _kill_by_pid(self, pid: int) -> None:
        sig = getattr(signal, self.signal_type, signal.SIGKILL)
        try:
            proc = psutil.Process(pid)
            proc.send_signal(sig)
            self._killed_pids.append(pid)
        except psutil.NoSuchProcess as exc:
            raise RuntimeError(f"PID {pid} not found") from exc

    def _kill_container(self) -> None:
        result = subprocess.run(
            ["docker", "kill", "--signal", self.signal_type, self.container_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"docker kill failed: {result.stderr.strip()}"
            )