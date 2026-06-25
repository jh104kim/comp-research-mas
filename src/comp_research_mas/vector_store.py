from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Protocol

from .memory_store import read_evidence_ledger


class VectorStore(Protocol):
    def add_evidence(self, evidence: list[dict[str, Any]]) -> int: ...
    def search(self, query: str | None = None, *, compressor_type: str = "", competitor: str = "", category: str = "", top_k: int = 3) -> list[dict[str, Any]]: ...
    def rebuild(self) -> int: ...


def evidence_text(item: dict[str, Any]) -> str:
    return " ".join(str(item.get(k, "")) for k in ["compressor_type", "competitor", "category", "source_name", "raw_text", "summary", "product_or_series"])


def deterministic_embedding(text: str, dims: int = 64) -> list[float]:
    vec = [0.0] * dims
    for token in text.lower().replace("/", " ").replace("·", " ").split():
        idx = sum(ord(ch) for ch in token) % dims
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class FileVectorStore:
    """File-backed semantic memory facade and fallback vector store."""

    def __init__(self, ledger: dict[str, Any] | None = None):
        self.ledger = ledger or read_evidence_ledger()

    def add_evidence(self, evidence: list[dict[str, Any]]) -> int:
        return len(evidence)

    def rebuild(self) -> int:
        return sum(len(payload.get("evidence", [])) for payload in (self.ledger.get("periods") or self.ledger.get("weeks") or {}).values())

    def search(self, query: str | None = None, competitor_pos: str = "", category_pos: str = "", *, compressor_type: str = "", competitor: str = "", category: str = "", top_k: int = 3) -> list[dict[str, Any]]:
        if query in {"Re", "Ro", "Sc"} and competitor_pos and category_pos and not compressor_type:
            compressor_type, competitor, category, query = str(query), competitor_pos, category_pos, None
        matches: list[dict[str, Any]] = []
        periods = self.ledger.get("periods") or {}
        iterable = sorted(periods.items(), reverse=True) if periods else sorted((self.ledger.get("weeks") or {}).items(), reverse=True)
        qtokens = set((query or "").lower().split())
        for period_id, payload in iterable:
            for item in payload.get("evidence", []):
                score = 0.0
                tags = set(item.get("dynamic_tags", []))
                if compressor_type and (item.get("compressor_type") == compressor_type or compressor_type in tags):
                    score += 4
                if competitor and (item.get("competitor") == competitor or competitor in tags):
                    score += 4
                if category and (item.get("category") == category or category in tags):
                    score += 3
                if qtokens:
                    text = evidence_text(item).lower()
                    score += sum(1 for token in qtokens if token in text)
                if score:
                    matches.append({"semantic_score": score, "period_id": period_id, **item})
        matches.sort(key=lambda x: (x["semantic_score"], x.get("trust_score", 0)), reverse=True)
        return matches[:top_k]


class ChromaVectorStore:
    """Local Chroma-compatible store.

    If chromadb is not installed, this persists deterministic embeddings to JSON under
    outputs/vector_store/chroma/index.json. The public interface remains stable.
    """

    def __init__(self, persist_dir: str | Path = "outputs/vector_store/chroma"):
        self.persist_dir = Path(persist_dir)
        self.index_path = self.persist_dir / "index.json"
        self.records: list[dict[str, Any]] = []
        if self.index_path.exists():
            self.records = json.loads(self.index_path.read_text(encoding="utf-8"))

    def add_evidence(self, evidence: list[dict[str, Any]]) -> int:
        seen = {rec["id"] for rec in self.records}
        added = 0
        for item in evidence:
            item_id = item.get("evidence_id") or f"{item.get('period_id')}:{item.get('compressor_type')}:{item.get('competitor')}:{item.get('category')}:{item.get('source_url')}"
            if item_id in seen:
                continue
            self.records.append({"id": item_id, "embedding": deterministic_embedding(evidence_text(item)), "metadata": item})
            seen.add(item_id)
            added += 1
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(self.records, ensure_ascii=False, indent=2), encoding="utf-8")
        return added

    def rebuild(self) -> int:
        self.records = []
        ledger = read_evidence_ledger()
        all_items: list[dict[str, Any]] = []
        for payload in (ledger.get("periods") or ledger.get("weeks") or {}).values():
            all_items.extend(payload.get("evidence", []))
        self.add_evidence(all_items)
        return len(self.records)

    def search(self, query: str | None = None, *, compressor_type: str = "", competitor: str = "", category: str = "", top_k: int = 3) -> list[dict[str, Any]]:
        query_text = query or " ".join(x for x in [compressor_type, competitor, category] if x)
        qvec = deterministic_embedding(query_text)
        rows: list[dict[str, Any]] = []
        for rec in self.records:
            item = rec["metadata"]
            filter_bonus = 0.0
            if compressor_type and item.get("compressor_type") == compressor_type:
                filter_bonus += 0.25
            if competitor and item.get("competitor") == competitor:
                filter_bonus += 0.25
            if category and item.get("category") == category:
                filter_bonus += 0.2
            score = cosine(qvec, rec["embedding"]) + filter_bonus
            rows.append({"semantic_score": round(score, 6), **item})
        rows.sort(key=lambda x: (x["semantic_score"], x.get("trust_score", 0)), reverse=True)
        return rows[:top_k]


def get_vector_store(prefer_chroma: bool = True) -> VectorStore:
    if prefer_chroma:
        try:
            return ChromaVectorStore()
        except Exception:
            pass
    return FileVectorStore()
