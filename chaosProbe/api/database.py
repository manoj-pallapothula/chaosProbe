"""
Database setup — SQLAlchemy + PostgreSQL.
Stores experiment runs and results.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Boolean, JSON, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from chaosProbe.utils.config import settings

Base = declarative_base()


class ExperimentRunDB(Base):
    __tablename__ = "experiment_runs"

    experiment_id = Column(String, primary_key=True)
    experiment_name = Column(String, nullable=False)
    started_at = Column(Float, nullable=False)
    ended_at = Column(Float, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    verdict = Column(String, nullable=False, default="pending")
    slo_breached = Column(Boolean, default=False)
    abort_reason = Column(String, nullable=True)
    pre_checks = Column(JSON, default=list)
    post_checks = Column(JSON, default=list)
    fault_result = Column(JSON, nullable=True)
    timeline = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_engine():
    return create_engine(settings.database_url)


def get_session_factory(engine):
    return sessionmaker(bind=engine)


def init_db(engine):
    Base.metadata.create_all(engine)


def get_db(session_factory) -> Session:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()