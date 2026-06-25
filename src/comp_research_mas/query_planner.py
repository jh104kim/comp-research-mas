from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import COMPETITOR_KEYWORDS, DEFAULT_WEEK_ID, SOURCE_PRIORITY, TYPE_REFRIGERANTS
from .models import CATEGORIES, PRIMARY_COMPETITORS, SECONDARY_COMPETITORS

PRIORITY_CATEGORIES = ("신제품·라인업", "신냉매·냉매전환", "성능·효율", "규격·인증")


def build_query_plan(week_id: str = DEFAULT_WEEK_ID) -> dict[str, Any]:
    queries: list[dict[str, Any]] = []
    for ctype in ("Re", "Ro", "Sc"):
        for competitor in PRIMARY_COMPETITORS[ctype]:
            for category in PRIORITY_CATEGORIES:
                queries.append(_query(week_id, ctype, competitor, category, "primary"))
        # Keep secondary narrower to reduce noise.
        for competitor in SECONDARY_COMPETITORS[ctype]:
            for category in ("신제품·라인업", "성능·효율"):
                queries.append(_query(week_id, ctype, competitor, category, "secondary"))
    return {"week_id": week_id, "queries": queries, "source_priority": SOURCE_PRIORITY}


def _query(week_id: str, ctype: str, competitor: str, category: str, priority: str) -> dict[str, Any]:
    refs = TYPE_REFRIGERANTS[ctype]
    competitor_terms = COMPETITOR_KEYWORDS.get(competitor, [competitor])
    type_term = {"Re": "reciprocating", "Ro": "rotary", "Sc": "scroll"}[ctype]
    keywords = [
        f"{' '.join(competitor_terms)} {type_term} compressor {' '.join(refs[:2])} {category} 2026",
        f"{competitor_terms[0]} compressor {' '.join(refs)} {type_term} news",
    ]
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
    }


def save_query_plan(plan: dict[str, Any], output_dir: str | Path = "outputs/search") -> Path:
    path = Path(output_dir) / f"{plan['week_id']}_query_plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
