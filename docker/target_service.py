"""
Target Service — a realistic FastAPI service that ChaosProbe attacks.
Exposes /health, /work, /metrics, and chaos injection endpoints.
"""
import os
import time
import random
import asyncio

from fastapi import FastAPI, Response
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST,
)
import psutil

SERVICE_NAME = os.getenv("SERVICE_NAME", "target-api")
PORT = int(os.getenv("PORT", "8081"))

app = FastAPI(title=SERVICE_NAME)

# ── Prometheus metrics ────────────────────────────────────────────────────────
request_count = Counter(
    "target_requests_total",
    "Total requests",
    ["service", "endpoint", "status"],
)
request_latency = Histogram(
    "target_request_duration_seconds",
    "Request latency",
    ["service", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)
error_rate = Gauge(
    "target_error_rate",
    "Current error rate (0-1)",
    ["service"],
)
cpu_usage = Gauge("target_cpu_usage_percent", "CPU usage", ["service"])
memory_usage = Gauge("target_memory_usage_bytes", "Memory usage", ["service"])

# Runtime state
_injected_latency_ms: float = 0.0
_injected_error_rate: float = 0.0


@app.on_event("startup")
async def start_metrics_collector():
    asyncio.create_task(_collect_system_metrics())


async def _collect_system_metrics():
    while True:
        cpu_usage.labels(service=SERVICE_NAME).set(psutil.cpu_percent())
        memory_usage.labels(service=SERVICE_NAME).set(
            psutil.Process().memory_info().rss
        )
        await asyncio.sleep(5)


@app.get("/health")
async def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/work")
async def do_work():
    start = time.perf_counter()
    endpoint = "/work"

    if _injected_latency_ms > 0:
        await asyncio.sleep(_injected_latency_ms / 1000)

    if random.random() < _injected_error_rate:
        duration = time.perf_counter() - start
        request_latency.labels(service=SERVICE_NAME, endpoint=endpoint).observe(duration)
        request_count.labels(service=SERVICE_NAME, endpoint=endpoint, status="500").inc()
        error_rate.labels(service=SERVICE_NAME).set(_injected_error_rate)
        return Response(status_code=500, content="Injected error")

    result = sum(i * i for i in range(random.randint(1000, 5000)))
    duration = time.perf_counter() - start

    request_latency.labels(service=SERVICE_NAME, endpoint=endpoint).observe(duration)
    request_count.labels(service=SERVICE_NAME, endpoint=endpoint, status="200").inc()
    error_rate.labels(service=SERVICE_NAME).set(_injected_error_rate)

    return {"result": result, "duration_ms": round(duration * 1000, 2)}


@app.post("/chaos/inject-latency")
async def inject_latency(latency_ms: float):
    global _injected_latency_ms
    _injected_latency_ms = latency_ms
    return {"injected_latency_ms": latency_ms}


@app.post("/chaos/inject-errors")
async def inject_errors(error_rate_pct: float):
    global _injected_error_rate
    _injected_error_rate = min(1.0, error_rate_pct / 100)
    return {"injected_error_rate": _injected_error_rate}


@app.post("/chaos/reset")
async def reset():
    global _injected_latency_ms, _injected_error_rate
    _injected_latency_ms = 0.0
    _injected_error_rate = 0.0
    return {"status": "reset"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)