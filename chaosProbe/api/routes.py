"""
API routes for ChaosProbe.
"""
from __future__ import annotations

import threading
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from chaosProbe.api.models import ExperimentRequest, ExperimentRunResponse
from chaosProbe.api.database import ExperimentRunDB, get_db
from chaosProbe.engine.experiment import Experiment
from chaosProbe.engine.orchestrator import Orchestrator
from chaosProbe.monitoring.prometheus_client import PrometheusClient
from chaosProbe.monitoring.slo_monitor import SLOMonitor
from chaosProbe.utils.config import settings
from chaosProbe.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _save_run(session: Session, run_dict: dict[str, Any]) -> None:
    db_run = ExperimentRunDB(
        experiment_id=run_dict["experiment_id"],
        experiment_name=run_dict["experiment_name"],
        started_at=run_dict["started_at"],
        ended_at=run_dict.get("ended_at"),
        duration_seconds=run_dict.get("duration_seconds"),
        verdict=run_dict["verdict"],
        slo_breached=run_dict.get("slo_breached", False),
        abort_reason=run_dict.get("abort_reason"),
        pre_checks=run_dict.get("pre_checks", []),
        post_checks=run_dict.get("post_checks", []),
        fault_result=run_dict.get("fault_result"),
        timeline=run_dict.get("timeline", []),
    )
    session.add(db_run)
    session.commit()


@router.post("/experiments/run", response_model=ExperimentRunResponse)
def run_experiment(
    request: ExperimentRequest,
    session: Session = Depends(get_db),
):
    """Trigger a chaos experiment and return the result."""
    try:
        # Build experiment from request
        experiment = Experiment.from_dict(request.model_dump())

        # Build SLO monitor
        prom = PrometheusClient(base_url=settings.prometheus_url)
        slo_monitor = SLOMonitor(prometheus_client=prom)

        # Run experiment
        orchestrator = Orchestrator(slo_monitor=slo_monitor)
        run = orchestrator.run(experiment)
        run_dict = run.to_dict()

        # Save to database
        try:
            _save_run(session, run_dict)
        except Exception as db_exc:
            logger.warning(f"[api] Failed to save run to DB: {db_exc}")

        return ExperimentRunResponse(**run_dict)

    except Exception as exc:
        logger.error(f"[api] Experiment failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/experiments", response_model=list[ExperimentRunResponse])
def list_experiments(
    limit: int = 20,
    session: Session = Depends(get_db),
):
    """List all past experiment runs."""
    try:
        runs = (
            session.query(ExperimentRunDB)
            .order_by(ExperimentRunDB.started_at.desc())
            .limit(limit)
            .all()
        )
        return [
            ExperimentRunResponse(
                experiment_id=r.experiment_id,
                experiment_name=r.experiment_name,
                started_at=r.started_at,
                ended_at=r.ended_at,
                duration_seconds=r.duration_seconds,
                verdict=r.verdict,
                slo_breached=r.slo_breached,
                abort_reason=r.abort_reason,
                pre_checks=r.pre_checks or [],
                post_checks=r.post_checks or [],
                fault_result=r.fault_result,
                timeline=r.timeline or [],
            )
            for r in runs
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/experiments/{experiment_id}", response_model=ExperimentRunResponse)
def get_experiment(
    experiment_id: str,
    session: Session = Depends(get_db),
):
    """Get a specific experiment run by ID."""
    run = session.query(ExperimentRunDB).filter(
        ExperimentRunDB.experiment_id == experiment_id
    ).first()

    if not run:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return ExperimentRunResponse(
        experiment_id=run.experiment_id,
        experiment_name=run.experiment_name,
        started_at=run.started_at,
        ended_at=run.ended_at,
        duration_seconds=run.duration_seconds,
        verdict=run.verdict,
        slo_breached=run.slo_breached,
        abort_reason=run.abort_reason,
        pre_checks=run.pre_checks or [],
        post_checks=run.post_checks or [],
        fault_result=run.fault_result,
        timeline=run.timeline or [],
    )


@router.delete("/experiments/{experiment_id}")
def delete_experiment(
    experiment_id: str,
    session: Session = Depends(get_db),
):
    """Delete an experiment run by ID."""
    run = session.query(ExperimentRunDB).filter(
        ExperimentRunDB.experiment_id == experiment_id
    ).first()

    if not run:
        raise HTTPException(status_code=404, detail="Experiment not found")

    session.delete(run)
    session.commit()
    return {"deleted": experiment_id}