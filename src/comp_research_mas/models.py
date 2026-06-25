from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchItem:
    competitor: str
    product: str
    refrigerant: str
    compressor_type: str
    source_url: str
    source_date: str
    summary: str
    samsung_gap_note: str = ""


@dataclass
class WeeklyReport:
    title: str
    markdown: str
    items: list[SearchItem] = field(default_factory=list)
    revision: int = 0


@dataclass
class CriticReview:
    score: int
    passed: bool
    findings: list[str]
    required_fixes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "findings": self.findings,
            "required_fixes": self.required_fixes,
        }
