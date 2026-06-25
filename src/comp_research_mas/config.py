from __future__ import annotations

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
]
