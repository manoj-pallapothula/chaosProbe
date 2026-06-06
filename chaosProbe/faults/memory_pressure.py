"""
Memory Pressure Fault
Allocates and holds a chunk of memory for the experiment duration.
Uses mmap for realistic OS-level memory pressure.
"""
from __future__ import annotations

import mmap
import threading
import time
from typing import Any

from chaosProbe.faults.base import BaseFault, FaultResult, FaultState
from chaosProbe.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryPressureFault(BaseFault):
    fault_type = "memory_pressure"

    def __init__(
        self,
        target: str,
        duration_seconds: int,
        memory_mb: int = 256,
        **kwargs: Any,
    ):
        super().__init__(target, duration_seconds, **kwargs)
        self.memory_mb = memory_mb
        self._mmap: mmap.mmap | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def inject(self) -> FaultResult:
        logger.info(
            f"[memory_pressure] Allocating {self.memory_mb}MB on {self.target} "
            f"for {self.duration_seconds}s"
        )
        self._result.state = FaultState.INJECTING
        try:
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._hold_memory, daemon=True
            )
            self._thread.start()
            time.sleep(0.1)
            self._result.state = FaultState.ACTIVE
            self._result.metadata = {
                "memory_mb": self.memory_mb,
                "memory_bytes": self.memory_mb * 1024 * 1024,
            }
            logger.info(f"[memory_pressure] Active — {self.memory_mb}MB allocated")
        except Exception as exc:
            self._mark_failed(str(exc))
            logger.error(f"[memory_pressure] Injection failed: {exc}")
        return self._result

    def recover(self) -> FaultResult:
        self._result.state = FaultState.RECOVERING
        try:
            self._stop_event.set()
            if self._thread:
                self._thread.join(timeout=5)
            self._mark_recovered()
            logger.info("[memory_pressure] Recovered — memory released")
        except Exception as exc:
            self._mark_failed(str(exc))
            logger.error(f"[memory_pressure] Recovery failed: {exc}")
        return self._result

    def _hold_memory(self) -> None:
        size = self.memory_mb * 1024 * 1024
        try:
            mem = mmap.mmap(-1, size)
            mem.write(b"\x00" * size)
            deadline = time.time() + self.duration_seconds
            while not self._stop_event.is_set() and time.time() < deadline:
                time.sleep(0.5)
            mem.close()
        except Exception as exc:
            logger.error(f"[memory_pressure] Memory hold failed: {exc}")
            self._mark_failed(str(exc))