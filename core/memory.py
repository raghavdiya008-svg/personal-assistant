"""
Sovereign Memory Layer for Project JARVIS.
Combines:
1. Relational Database (SQLite via SQLAlchemy) for structured state, leads, and invoices.
2. Local Vector Store (ChromaDB) for unstructured knowledge, call transcripts, and objections.
"""

import uuid
import datetime
import logging
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from core.config import settings

logger = logging.getLogger("JARVIS.Memory")

Base = declarative_base()


class Lead(Base):
    """Represents a potential client or customer."""
    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    status = Column(String, default="NEW")  # NEW, QUALIFIED, MEETING_BOOKED, CLOSED, LOST
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    calls = relationship("CallRecord", back_populates="lead", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="lead", cascade="all, delete-orphan")


class CallRecord(Base):
    """Represents an autonomous Google Meet call."""
    __tablename__ = "call_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    scheduled_time = Column(DateTime, nullable=False)
    meet_url = Column(String, nullable=False)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    deal_outcome = Column(String, default="PENDING")  # PENDING, CLOSED_WON, CLOSED_LOST, FOLLOW_UP
    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    lead = relationship("Lead", back_populates="calls")


class Invoice(Base):
    """Represents a Stripe payment link / invoice generated post-call."""
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)
    stripe_link = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="DRAFT")  # DRAFT, SENT, PAID, CANCELLED
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)

    lead = relationship("Lead", back_populates="invoices")


class AgentTask(Base):
    """Queue and history of background agent tasks."""
    __tablename__ = "agent_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_name = Column(String, index=True, nullable=False)
    task_type = Column(String, nullable=False)
    payload = Column(Text, nullable=True)
    status = Column(String, default="QUEUED")  # QUEUED, RUNNING, COMPLETED, FAILED
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


class MemoryFact(Base):
    """Persistent user preferences, project facts, and knowledge ledger."""
    __tablename__ = "memory_facts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String, default="GENERAL")  # PREFERENCE, PROJECT, IDENTITY, NOTE
    key = Column(String, index=True, nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


# Relational DB Engine Setup
engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def store_fact(key: str, value: str, category: str = "GENERAL") -> MemoryFact:
    """Store or update a persistent fact in the database."""
    with get_db_session() as db:
        existing = db.query(MemoryFact).filter(MemoryFact.key == key).first()
        if existing:
            existing.value = value
            existing.category = category
            return existing
        fact = MemoryFact(key=key, value=value, category=category)
        db.add(fact)
        return fact


def retrieve_relevant_facts(query: str, limit: int = 5) -> List[Dict[str, str]]:
    """Search for relevant facts from the relational memory ledger."""
    terms = [t.lower() for t in query.split() if len(t) > 2]
    if not terms:
        return []
    with get_db_session() as db:
        all_facts = db.query(MemoryFact).all()
        scored = []
        for f in all_facts:
            text = f"{f.key} {f.value} {f.category}".lower()
            score = sum(text.count(t) for t in terms)
            if score > 0:
                scored.append((score, {"key": f.key, "value": f.value, "category": f.category}))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]


class VectorMemory:
    """Local Vector Store using ChromaDB for knowledge base and transcripts."""

    def __init__(self):
        self.client = None
        self._init_chroma()

    def _init_chroma(self):
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=str(settings.VECTOR_DIR))
            self.knowledge_collection = self.client.get_or_create_collection(name="knowledge_base")
            self.transcript_collection = self.client.get_or_create_collection(name="call_transcripts")
            logger.info("ChromaDB Vector Store initialized successfully.")
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}")

    def add_knowledge(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Add documentation or business facts to vector memory."""
        if self.client:
            kwargs = {
                "ids": [doc_id],
                "documents": [text]
            }
            if metadata:
                kwargs["metadatas"] = [metadata]
            self.knowledge_collection.upsert(**kwargs)


    def search_knowledge(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieve most relevant context for client questions."""
        if not self.client:
            return []
        try:
            results = self.knowledge_collection.query(
                query_texts=[query],
                n_results=top_k
            )
            return results["documents"][0] if results and "documents" in results else []
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []


# Database Helpers
from contextlib import contextmanager

@contextmanager
def get_db_session():
    """Context manager for safe database sessions with automatic rollback on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


vector_memory = VectorMemory()
