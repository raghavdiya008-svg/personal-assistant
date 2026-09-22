"""Unit tests for SQLite Memory and ChromaDB."""

import pytest
import datetime
from core.memory import SessionLocal, Lead, CallRecord, Invoice, vector_memory


def test_sqlite_lead_and_call_lifecycle():
    db = SessionLocal()
    try:
        # Create Lead
        lead = Lead(email="test.lead@domain.com", name="Test Lead", status="NEW")
        db.add(lead)
        db.commit()
        db.refresh(lead)

        assert lead.id is not None
        assert lead.email == "test.lead@domain.com"

        # Create Call Record
        call = CallRecord(
            lead_id=lead.id,
            scheduled_time=datetime.datetime.utcnow(),
            meet_url="https://meet.google.com/test-meet",
            deal_outcome="SCHEDULED"
        )
        db.add(call)
        db.commit()

        # Query and verify relationship
        fetched_lead = db.query(Lead).filter(Lead.email == "test.lead@domain.com").first()
        assert len(fetched_lead.calls) == 1
        assert fetched_lead.calls[0].meet_url == "https://meet.google.com/test-meet"

        # Cleanup test entry
        db.delete(fetched_lead)
        db.commit()
    finally:
        db.close()


def test_vector_memory_search():
    vector_memory.add_knowledge("doc_1", "Our AI agent autonomously joins Google Meet.")
    results = vector_memory.search_knowledge("Google Meet")
    assert isinstance(results, list)
