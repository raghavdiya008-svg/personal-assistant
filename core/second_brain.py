"""
Local 'Second Brain' RAG Engine for Project JARVIS v2 (Khoj Architecture).

Indexes and searches personal files, markdown notes, PDFs, and records locally
without leaking private data to third-party cloud models.
"""

import os
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.config import settings
from core.trust import TrustGuard, TrustedPayload
from core.capability_broker import capability_broker, CapabilityDefinition, RiskLevel

logger = logging.getLogger("JARVIS.SecondBrain")


class LocalSecondBrain:
    """
    Offline private knowledge base.
    Ingests personal documents, generates local chunked indexes, and performs
    similarity search completely locally.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.brain_dir = storage_dir or (settings.DATA_DIR / "second_brain")
        self.brain_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.brain_dir / "knowledge_index.json"
        self._index: List[Dict[str, Any]] = self._load_index()

    def _load_index(self) -> List[Dict[str, Any]]:
        if self.index_file.exists():
            try:
                return json.loads(self.index_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load knowledge index: {e}")
        return []

    def _save_index(self):
        self.index_file.write_text(json.dumps(self._index, indent=2), encoding="utf-8")

    def index_document(self, file_path: Optional[str] = None, path: Optional[str] = None, tags: Optional[List[str]] = None, **kwargs) -> TrustedPayload:
        """
        Ingest a personal document (Markdown, Text, JSON, PDF) into the local index.
        """
        target = file_path or path or kwargs.get("filepath") or kwargs.get("doc_path")
        if not target:
            raise ValueError("Parameter 'file_path' or 'path' is required.")

        path_obj = Path(target).resolve()
        if not path_obj.exists():
            raise FileNotFoundError(f"Document not found: {target}")

        # Extract text content safely
        content = ""
        if path_obj.suffix.lower() in (".md", ".txt", ".json", ".csv"):
            content = path_obj.read_text(encoding="utf-8", errors="replace")
        elif path_obj.suffix.lower() == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path_obj))
                content = "\n".join([page.extract_text() or "" for page in reader.pages])
            except ImportError:
                content = f"[PDF file: {path_obj.name} - text extractor pypdf not installed]"
        else:
            content = path_obj.read_text(encoding="utf-8", errors="replace")

        # Chunk content into paragraphs
        paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
        doc_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Remove previous chunks for this document
        self._index = [item for item in self._index if item.get("source") != str(path_obj)]

        for idx, chunk in enumerate(paragraphs):
            self._index.append({
                "source": str(path_obj),
                "filename": path_obj.name,
                "chunk_id": f"{doc_hash[:8]}_{idx}",
                "content": chunk,
                "tags": tags or [],
            })

        self._save_index()
        logger.info(f"🧠 [SECOND BRAIN] Indexed {len(paragraphs)} chunks from: {path_obj.name}")
        return TrustGuard.wrap_system({
            "source": str(path_obj),
            "chunks_indexed": len(paragraphs),
            "status": "INDEXED",
        }, source="second_brain.index")

    def query(self, search_text: Optional[str] = None, query: Optional[str] = None, text: Optional[str] = None, top_k: int = 5, **kwargs) -> TrustedPayload:
        """
        Search the private local second brain without sending personal data to the cloud.
        Uses local term-frequency keyword matching across chunks.
        """
        q = search_text or query or text or kwargs.get("q", "")
        terms = [t.lower() for t in q.split() if len(t) > 2]
        scored_results = []

        for item in self._index:
            chunk_lower = item["content"].lower()
            score = sum(chunk_lower.count(t) for t in terms)
            if score > 0:
                scored_results.append((score, item))

        # Sort by relevance score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        top_matches = [item for score, item in scored_results[:top_k]]

        logger.info(f"🔍 [SECOND BRAIN QUERY] Found {len(top_matches)} matches for '{q}'")
        return TrustGuard.wrap_system({
            "query": q,
            "results": top_matches,
            "count": len(top_matches),
        }, source="second_brain.search")


# Singleton instance
second_brain = LocalSecondBrain()

# Register capabilities with Capability Broker
capability_broker.register(
    CapabilityDefinition(
        name="second_brain.index",
        risk_level=RiskLevel.LOW,
        handler=second_brain.index_document,
        requires_approval=False,
        allowed_agents=["*"],
    )
)
capability_broker.register(
    CapabilityDefinition(
        name="second_brain.search",
        risk_level=RiskLevel.LOW,
        handler=second_brain.query,
        requires_approval=False,
        allowed_agents=["*"],
    )
)
