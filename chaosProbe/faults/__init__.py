"""Fault injector registry."""
from chaosProbe.faults.base import BaseFault, FaultResult, FaultState
from chaosProbe.faults.cpu_stress import CpuStressFault
from chaosProbe.faults.memory_pressure import MemoryPressureFault
from chaosProbe.faults.latency_injection import LatencyInjectionFault
from chaosProbe.faults.process_kill import ProcessKillFault

FAULT_REGISTRY: dict[str, type[BaseFault]] = {
    "cpu_stress": CpuStressFault,
    "memory_pressure": MemoryPressureFault,
    "latency_injection": LatencyInjectionFault,
    "process_kill": ProcessKillFault,
}

__all__ = [
    "BaseFault",
    "FaultResult",
    "FaultState",
    "CpuStressFault",
    "MemoryPressureFault",
    "LatencyInjectionFault",
    "ProcessKillFault",
    "FAULT_REGISTRY",
]