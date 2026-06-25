from __future__ import annotations

from typing import Any

from .memory_store import read_evidence_ledger
from .vector_store import get_vector_store


def retrieve_related_evidence(*, compressor_type: str, competitor: str, category: str, limit: int = 3) -> list[dict[str, Any]]:
    store = get_vector_store(prefer_chroma=True)
    try:
        if hasattr(store, "records") and not getattr(store, "records"):
            store.rebuild()
        matches = store.search(compressor_type=compressor_type, competitor=competitor, category=category, top_k=limit)
        if matches:
            return matches
    except Exception:
        pass
    ledger = read_evidence_ledger()
    return get_vector_store(prefer_chroma=False).search(compressor_type=compressor_type, competitor=competitor, category=category, top_k=limit)
