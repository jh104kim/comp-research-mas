from __future__ import annotations

from typing import Any

from .memory_store import read_evidence_ledger


class FileVectorStore:
    """
    File-backed semantic memory facade.
    embedding/vector index 없음. Chroma/FAISS 교체 가능한 interface만 고정.
    """

    def __init__(self, ledger: dict[str, Any] | None = None):
        self.ledger = ledger or read_evidence_ledger()

    def search(self, compressor_type: str, competitor: str, category: str, top_k: int = 3) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        periods = self.ledger.get("periods") or {}
        if periods:
            iterable = sorted(periods.items(), reverse=True)
        else:
            iterable = sorted((self.ledger.get("weeks") or {}).items(), reverse=True)
        for period_id, payload in iterable:
            for item in payload.get("evidence", []):
                score = 0
                tags = set(item.get("dynamic_tags", []))
                if item.get("compressor_type") == compressor_type or compressor_type in tags:
                    score += 4
                if item.get("competitor") == competitor or competitor in tags:
                    score += 4
                if item.get("category") == category or category in tags:
                    score += 3
                if score:
                    matches.append({"semantic_score": score, "period_id": period_id, **item})
        matches.sort(key=lambda x: (x["semantic_score"], x.get("trust_score", 0)), reverse=True)
        return matches[:top_k]
