from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, TypedDict

CompressorType = Literal["Re", "Ro", "Sc"]
SamsungStatus = Literal["보유", "미보유", "대응 중", "확인 필요"]

CATEGORIES: tuple[str, ...] = (
    "신냉매·냉매 전환",
    "성능·효율",
    "신제품·라인업",
    "신뢰성·내구성",
    "특허·기술",
    "규격·인증",
    "가격·유통",
    "전시회·발표",
)

TYPE_LABELS: dict[str, str] = {
    "Re": "Reciprocating",
    "Ro": "Rotary",
    "Sc": "Scroll",
}

RE_PRIMARY = ["GMCC/Midea", "LG"]
RE_SECONDARY = ["Embraco/Nidec", "Secop", "Panasonic"]
RO_PRIMARY = ["GMCC/Midea", "LG"]
RO_SECONDARY = ["Highly", "Panasonic"]
SC_PRIMARY = ["Copeland/Emerson"]
SC_SECONDARY = ["GMCC/Midea", "Danfoss", "LG"]

PRIMARY_COMPETITORS: dict[str, list[str]] = {
    "Re": RE_PRIMARY,
    "Ro": RO_PRIMARY,
    "Sc": SC_PRIMARY,
}

SECONDARY_COMPETITORS: dict[str, list[str]] = {
    "Re": RE_SECONDARY,
    "Ro": RO_SECONDARY,
    "Sc": SC_SECONDARY,
}

COMPETITOR_ALIASES: dict[str, str] = {
    "GMCC": "GMCC/Midea",
    "Midea": "GMCC/Midea",
    "Copeland": "Copeland/Emerson",
    "Emerson": "Copeland/Emerson",
    "Embraco": "Embraco/Nidec",
    "Nidec": "Embraco/Nidec",
}

NO_EVIDENCE_TEXT = "해당 없음 — 이번 주 확인된 고신뢰 근거 없음"
SAMSUNG_STATUSES = ("보유", "미보유", "대응 중", "확인 필요")


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
    hard_fail: bool = False
    hard_fail_reasons: list[str] = field(default_factory=list)
    iteration: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "findings": self.findings,
            "required_fixes": self.required_fixes,
            "hard_fail": self.hard_fail,
            "hard_fail_reasons": self.hard_fail_reasons,
            "iteration": self.iteration,
        }


@dataclass(frozen=True)
class EvidenceItem:
    compressor_type: str
    competitor: str
    summary: str
    samsung_status: str
    category: str = "신제품·라인업"
    product_or_series: str = "확인 필요"
    refrigerant: str = "확인 필요"
    condition_or_capacity: str = "확인 필요"
    application: str = "Residential/Unitary/Heat pump"
    source_name: str = "수동 입력"
    source_url: str = "manual://step1"
    source_date: str = "확인 필요"
    trust_score: int = 3
    is_primary: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WorkflowState(TypedDict, total=False):
    raw_data: str
    draft: str
    feedback: dict[str, Any]
    score: int
    iteration: int
    evidence: list[dict[str, Any]]
    gap_table: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    status: str
    error_log: list[str]
    hard_fail: bool
    output_paths: dict[str, str]
