"""
Authoritative Database Persistence Layer for Project JARVIS v2.

Supports PostgreSQL 16 (production docker stack) with automatic fallback
to SQLite (local standalone development).
"""

from contextlib import contextmanager
import json
import logging
import os
import time
from typing import Generator, Dict, Any, Optional

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    Float,
    Boolean,
    JSON,
    DateTime,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from core.config import settings

logger = logging.getLogger("JARVIS.Database")

Base = declarative_base()


# ── ORM Models ───────────────────────────────────────────────────────────────

class SystemEventModel(Base):
    __tablename__ = "system_events_ledger"

    event_id = Column(String(64), primary_key=True)
    trace_id = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(64), nullable=False)
    trust_level = Column(String(32), nullable=False)
    event_type = Column(String(64), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(Float, default=time.time, nullable=False)


class ApprovalTicketModel(Base):
    __tablename__ = "approval_tickets_ledger"

    ticket_id = Column(String(64), primary_key=True)
    action_type = Column(String(64), nullable=False)
    risk_level = Column(String(16), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    details = Column(JSON, nullable=False)
    nonce = Column(String(64), unique=True, nullable=False)
    status = Column(String(16), default="PENDING", nullable=False, index=True)
    requested_by = Column(String(64), nullable=False)
    decided_by = Column(String(64), nullable=True)
    signature = Column(Text, nullable=True)
    issued_at = Column(Float, nullable=False)
    expires_at = Column(Float, nullable=False, index=True)
    executed_at = Column(Float, nullable=True)


class ConsentRecordModel(Base):
    __tablename__ = "consent_ledger"

    subject_identifier = Column(String(128), primary_key=True)
    channel = Column(String(32), primary_key=True)
    jurisdiction = Column(String(8), nullable=False)
    consent_status = Column(String(16), default="GRANTED", nullable=False)
    proof_source = Column(String(255), nullable=False)
    obtained_at = Column(Float, nullable=False)
    expires_at = Column(Float, nullable=True)
    withdrawn_at = Column(Float, nullable=True)


class StagedToolModel(Base):
    __tablename__ = "staged_tools_ledger"

    tool_id = Column(String(64), primary_key=True)
    name = Column(String(64), nullable=False)
    version = Column(String(32), nullable=False)
    code_hash = Column(String(64), nullable=False)
    source_code = Column(Text, nullable=False)
    permissions = Column(JSON, nullable=False)
    stage = Column(String(32), default="GENERATED", nullable=False)
    test_results = Column(JSON, default=dict)
    security_audit = Column(JSON, default=dict)
    signed_by = Column(String(64), nullable=True)
    created_at = Column(Float, default=time.time)


# ── Engine & Session Management ──────────────────────────────────────────────

def _get_engine():
    # Attempt Postgres connection from environment, fallback to SQLite
    pg_user = os.getenv("POSTGRES_USER", "jarvis")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "jarvis_secure_pass")
    pg_db = os.getenv("POSTGRES_DB", "jarvis_state")
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_PORT", "5432")

    pg_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    sqlite_url = f"sqlite:///{settings.DATA_DIR / 'jarvis_v2.db'}"

    # Try Postgres ping if configured
    if os.getenv("USE_POSTGRES", "").lower() in ("true", "1"):
        try:
            engine = create_engine(pg_url, pool_pre_ping=True)
            with engine.connect():
                logger.info(f"Connected to PostgreSQL authoritative store at {pg_host}:{pg_port}/{pg_db}")
                return engine
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed ({e}); falling back to local SQLite.")

    # SQLite fallback (guaranteed to work locally without containers)
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    logger.info(f"Using SQLite authoritative store at {sqlite_url}")
    return engine


engine = _get_engine()
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_v2_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session with auto-rollback on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction rolled back: {e}")
        raise
    finally:
        session.close()
