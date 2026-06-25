from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    CATEGORIES,
    COMPETITOR_ALIASES,
    PRIMARY_COMPETITORS,
    SECONDARY_COMPETITORS,
    SOURCE_TRUST_SCORE,
    TYPE_LABELS,
)

REPORT_TITLE = "압축기 경쟁사 월간 모니터링 리포트"
PASS_SCORE = 7
MAX_ITERATIONS = 2
DEFAULT_WEEK_ID = "2026-26"

SOURCE_PRIORITY = {
    "tier1": ["NaturalRefrigerants.com", "Cooling Post", "Chillventa"],
    "tier2": ["ACHR News", "AHR Expo", "ASHRAE"],
    "tier3": ["JARN", "China Refrigeration Expo"],
    "academic": ["International Journal of Refrigeration", "Applied Thermal Engineering"],
}

TYPE_REFRIGERANTS = {
    "Re": ["R290", "R600a", "R134a", "R1234yf"],
    "Ro": ["R290", "R32", "R454C"],
    "Sc": ["R454B", "R32", "R410A", "R466A"],
}



SOURCE_WHITELIST_PATH = Path("config/source_whitelist.yaml")

def load_source_whitelist(path: str | Path = SOURCE_WHITELIST_PATH) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))

def flatten_source_whitelist(path: str | Path = SOURCE_WHITELIST_PATH) -> list[dict[str, Any]]:
    data = load_source_whitelist(path)
    entries: list[dict[str, Any]] = []
    for group, payload in data.get("source_whitelist", {}).items():
        trust = int(payload.get("trust_score", 3)) if isinstance(payload, dict) else 3
        sources = payload.get("sources", []) if isinstance(payload, dict) else []
        for source in sources:
            item = dict(source)
            item["group"] = group
            item["trust_score"] = int(item.get("trust_score", trust))
            entries.append(item)
    return entries

def source_names_by_focus(*focus_terms: str, min_trust: int = 3) -> list[str]:
    terms = {str(term).lower() for term in focus_terms if term}
    names: list[str] = []
    for source in flatten_source_whitelist():
        focus = {str(item).lower() for item in source.get("focus", [])}
        if source.get("trust_score", 0) < min_trust:
            continue
        if "all" in focus or terms & focus:
            names.append(source["name"])
    return names

COMPETITOR_KEYWORDS = {
    "GMCC/Midea": ["GMCC", "Midea"],
    "LG": ["LG"],
    "Copeland/Emerson": ["Copeland", "Emerson"],
    "Embraco/Nidec": ["Embraco", "Nidec"],
    "Secop": ["Secop"],
    "Panasonic": ["Panasonic"],
    "Highly": ["Highly"],
    "Danfoss": ["Danfoss"],
}

__all__ = [
    "CATEGORIES",
    "COMPETITOR_ALIASES",
    "PRIMARY_COMPETITORS",
    "SECONDARY_COMPETITORS",
    "SOURCE_TRUST_SCORE",
    "TYPE_LABELS",
    "REPORT_TITLE",
    "PASS_SCORE",
    "MAX_ITERATIONS",
    "DEFAULT_WEEK_ID",
    "SOURCE_PRIORITY",
    "TYPE_REFRIGERANTS",
    "COMPETITOR_KEYWORDS",
    "SOURCE_WHITELIST_PATH",
    "load_source_whitelist",
    "flatten_source_whitelist",
    "source_names_by_focus",
]
