from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import COMPETITOR_KEYWORDS, DEFAULT_WEEK_ID, SOURCE_PRIORITY, TYPE_REFRIGERANTS, flatten_source_whitelist, source_names_by_focus
from .models import CATEGORIES, PRIMARY_COMPETITORS, SECONDARY_COMPETITORS

PRIORITY_CATEGORIES = ("신제품·라인업", "신냉매·냉매전환", "성능·효율", "규격·인증")


def build_query_plan(week_id: str = DEFAULT_WEEK_ID, period_id: str | None = None, source_boosts: list[str] | None = None) -> dict[str, Any]:
    queries: list[dict[str, Any]] = []
    source_boosts = source_boosts or []
    for ctype in ("Re", "Ro", "Sc"):
        for competitor in PRIMARY_COMPETITORS[ctype]:
            for category in PRIORITY_CATEGORIES:
                queries.append(_query(week_id, ctype, competitor, category, "primary", period_id=period_id, source_boosts=source_boosts))
        # Keep secondary narrower to reduce noise.
        for competitor in SECONDARY_COMPETITORS[ctype]:
            for category in ("신제품·라인업", "성능·효율"):
                queries.append(_query(week_id, ctype, competitor, category, "secondary", period_id=period_id, source_boosts=source_boosts))
    return {"week_id": week_id, "period_id": period_id or week_id, "queries": queries, "source_priority": SOURCE_PRIORITY, "source_whitelist": flatten_source_whitelist(), "source_boosts": source_boosts}


def _query(week_id: str, ctype: str, competitor: str, category: str, priority: str, *, period_id: str | None = None, source_boosts: list[str] | None = None) -> dict[str, Any]:
    refs = TYPE_REFRIGERANTS[ctype]
    competitor_terms = COMPETITOR_KEYWORDS.get(competitor, [competitor])
    type_term = {"Re": "reciprocating", "Ro": "rotary", "Sc": "scroll"}[ctype]
    period_text = period_id or week_id
    keywords = [
        f"{' '.join(competitor_terms)} {type_term} compressor {' '.join(refs[:2])} {category} {period_text}",
        f"{competitor_terms[0]} compressor {' '.join(refs)} {type_term} news {period_text}",
    ]
    if period_text.startswith("2025-"):
        quarter = (int(period_text[-2:]) - 1) // 3 + 1 if period_text[-2:].isdigit() else ""
        keywords.append(f"{' '.join(competitor_terms)} {type_term} compressor {period_text[:4]} Q{quarter}")
    preferred_sources = _preferred_sources(ctype, competitor, refs, category, source_boosts or [])
    query_id = f"{ctype}_{competitor.replace('/', '_').replace(' ', '')}_{category.replace('·', '').replace(' ', '')}"
    return {
        "query_id": query_id,
        "week_id": week_id,
        "compressor_type": ctype,
        "competitor": competitor,
        "category": category,
        "refrigerants": refs,
        "keywords": keywords,
        "priority": priority,
        "preferred_sources": preferred_sources,
    }



def _preferred_sources(ctype: str, competitor: str, refs: list[str], category: str, source_boosts: list[str]) -> list[str]:
    names: list[str] = []
    competitor_focus = {
        "GMCC/Midea": ["GMCC Official"],
        "LG": ["LG Compressor Official"],
        "Copeland/Emerson": ["Copeland Official"],
        "Embraco/Nidec": ["Embraco Official"],
        "Secop": ["Secop Official"],
        "Danfoss": ["Danfoss Compressor Official"],
    }.get(competitor, [])
    names.extend(competitor_focus)
    if "특허" in category:
        names.extend(["Google Patents", "Espacenet"])
    if "규격" in category or any(ref in {"R454B", "R32"} for ref in refs):
        names.extend(["EPA SNAP", "EU F-Gas Regulation", "ASHRAE"])
    names.extend(source_names_by_focus(ctype, *refs, min_trust=3))
    names.extend(source_boosts)
    deduped: list[str] = []
    for name in names:
        if name and name not in deduped:
            deduped.append(name)
    return deduped[:8]

def save_query_plan(plan: dict[str, Any], output_dir: str | Path = "outputs/search") -> Path:
    path = Path(output_dir) / f"{plan['week_id']}_query_plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def replan_query_plan(plan: dict[str, Any], *, evidence_count: int, threshold: int = 8) -> dict[str, Any]:
    """Dynamic replanning for deterministic retrofit.

    If evidence coverage is low, broaden primary queries to all categories and
    mark the plan as replanned. The live Hermes connection remains a later step.
    """
    if evidence_count >= threshold or plan.get("replanned"):
        return plan
    week_id = plan["week_id"]
    existing_ids = {q["query_id"] for q in plan["queries"]}
    queries = list(plan["queries"])
    for ctype in ("Re", "Ro", "Sc"):
        for competitor in PRIMARY_COMPETITORS[ctype]:
            for category in CATEGORIES:
                q = _query(week_id, ctype, competitor, category, "primary-replan", period_id=plan.get("period_id"), source_boosts=plan.get("source_boosts", []))
                if q["query_id"] not in existing_ids:
                    queries.append(q)
                    existing_ids.add(q["query_id"])
    return {**plan, "queries": queries, "period_id": plan.get("period_id", week_id), "replanned": True, "replan_reason": f"evidence_count {evidence_count} < threshold {threshold}"}
