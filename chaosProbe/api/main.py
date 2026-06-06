"""
ChaosProbe FastAPI application.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from chaosProbe.api.routes import router
from chaosProbe.api.database import get_engine, get_session_factory, init_db, get_db
from chaosProbe.api.models import HealthResponse
from chaosProbe.utils.config import settings
from chaosProbe.utils.logger import get_logger

logger = get_logger(__name__)

# ── Prometheus metrics ────────────────────────────────────────────────────────
experiments_total = Counter(
    "chaosProbe_experiments_total",
    "Total experiments run",
    ["verdict"],
)
experiment_duration = Histogram(
    "chaosProbe_experiment_duration_seconds",
    "Experiment duration",
    buckets=[10, 30, 60, 120, 300, 600],
)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ChaosProbe",
    description="Chaos Engineering Framework — fault injection, SLO monitoring, auto-rollback",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Database init ─────────────────────────────────────────────────────────────
engine = get_engine()
session_factory = get_session_factory(engine)

try:
    init_db(engine)
    logger.info("[api] Database initialized")
except Exception as exc:
    logger.warning(f"[api] Database init failed (running without DB): {exc}")


# Override get_db dependency with our session factory
def get_db_override():
    yield from get_db(session_factory)


app.dependency_overrides[get_db] = get_db_override

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        version="1.0.0",
        environment=settings.app_env,
    )


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
def root():
    return {
        "name": "ChaosProbe",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }