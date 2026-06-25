from __future__ import annotations

from typing import Any

from .memory_store import read_evidence_ledger


def retrieve_related_evidence(*, compressor_type: str, competitor: str, category: str, limit: int = 3) -> list[dict[str, Any]]:
    ledger = read_evidence_ledger()
    matches: list[dict[str, Any]] = []
    for week_id, payload in sorted(ledger.get("weeks", {}).items(), reverse=True):
        for item in payload.get("evidence", []):
            score = 0
            if item.get("compressor_type") == compressor_type:
                score += 3
            if item.get("competitor") == competitor:
                score += 3
            if item.get("category") == category:
                score += 2
            if score:
                matches.append({"score": score, "week_id": week_id, **item})
    matches.sort(key=lambda x: (x["score"], x.get("trust_score", 0)), reverse=True)
    return matches[:limit]
