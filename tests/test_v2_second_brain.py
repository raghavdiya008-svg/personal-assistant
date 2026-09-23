"""
Tests for Local Second Brain RAG Engine in Project JARVIS v2.
"""

import pytest
from pathlib import Path
from core.second_brain import LocalSecondBrain
from core.config import settings


@pytest.fixture
def brain(tmp_path):
    return LocalSecondBrain(storage_dir=tmp_path)


def test_index_and_query_document(brain, tmp_path):
    # Create test document
    doc = tmp_path / "enterprise_specs.md"
    doc.write_text(
        "Project JARVIS v2 enforces capability-based security boundaries.\n\n"
        "The cryptographic approval engine validates HMAC signatures on every action.\n\n"
        "PostgreSQL 16 serves as the authoritative persistence ledger.",
        encoding="utf-8",
    )

    # Index document
    index_res = brain.index_document(str(doc), tags=["architecture", "security"])
    assert index_res.content["status"] == "INDEXED"
    assert index_res.content["chunks_indexed"] >= 2

    # Query search
    search_res = brain.query("cryptographic approval HMAC", top_k=2)
    assert search_res.content["count"] >= 1
    top_hit = search_res.content["results"][0]
    assert "cryptographic" in top_hit["content"].lower()
    assert "enterprise_specs.md" in top_hit["filename"]
