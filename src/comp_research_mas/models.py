from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, TypedDict

CompressorType = Literal["Re", "Ro", "Sc"]
SamsungStatus = Literal["보유", "미보유", "대응중", "확인필요"]
Category = Literal[
    "신냉매·냉매전환",
    "성능·효율",
    "신제품·라인업",
    "신뢰성·내구성",
    "특허·기술",
    "규격·인증",
    "가격·유통",
    "전시회·발표",
]
SourceType = Literal["official", "exhibition", "patent", "academic", "trade_media", "news"]
ThreatLevel = Literal["high", "medium", "low", "none"]
SignalType = Literal["primary_new_entry", "multi_competitor_entry", "spec_change", "new_refrigerant"]

CATEGORIES: tuple[str, ...] = (
    "신냉매·냉매전환",
    "성능·효율",
    "신제품·라인업",
    "신뢰성·내구성",
    "특허·기술",
    "규격·인증",
    "가격·유통",
    "전시회·발표",
)

CATEGORY_ALIASES: dict[str, str] = {
    "신냉매·냉매 전환": "신냉매·냉매전환",
    "냉매전환": "신냉매·냉매전환",
    "냉매 전환": "신냉매·냉매전환",
}

TYPE_LABELS: dict[str, str] = {"Re": "Reciprocating", "Ro": "Rotary", "Sc": "Scroll"}

RE_PRIMARY = ["GMCC/Midea", "LG"]
RE_SECONDARY = ["Embraco/Nidec", "Secop", "Panasonic"]
RO_PRIMARY = ["GMCC/Midea", "LG"]
RO_SECONDARY = ["Highly", "Panasonic"]
SC_PRIMARY = ["Copeland/Emerson"]
SC_SECONDARY = ["GMCC/Midea", "Danfoss", "LG"]

PRIMARY_COMPETITORS: dict[str, list[str]] = {"Re": RE_PRIMARY, "Ro": RO_PRIMARY, "Sc": SC_PRIMARY}
SECONDARY_COMPETITORS: dict[str, list[str]] = {"Re": RE_SECONDARY, "Ro": RO_SECONDARY, "Sc": SC_SECONDARY}

COMPETITOR_ALIASES: dict[str, str] = {
    "GMCC": "GMCC/Midea",
    "Midea": "GMCC/Midea",
    "GMCC Midea": "GMCC/Midea",
    "Copeland": "Copeland/Emerson",
    "Emerson": "Copeland/Emerson",
    "Copeland Emerson": "Copeland/Emerson",
    "Embraco": "Embraco/Nidec",
    "Nidec": "Embraco/Nidec",
    "Embraco Nidec": "Embraco/Nidec",
}

NO_EVIDENCE_TEXT = "해당 없음 — 이번 달 확인된 고신뢰 근거 없음"
SAMSUNG_STATUSES = ("보유", "미보유", "대응중", "확인필요")
SOURCE_TYPES = ("official", "exhibition", "patent", "academic", "trade_media", "news")
THREAT_LEVELS = ("high", "medium", "low", "none")
SOURCE_TRUST_SCORE = {"official": 5, "exhibition": 5, "patent": 5, "academic": 4, "trade_media": 3, "news": 2}


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
        return asdict(self)


@dataclass(frozen=True)
class EvidenceItem:
    compressor_type: CompressorType = "Re"
    competitor: str = "확인필요"
    refrigerant: list[str] = field(default_factory=lambda: ["확인필요"])
    category: Category = "신제품·라인업"
    samsung_status: SamsungStatus = "확인필요"
    trust_score: int = 3
    source_type: SourceType = "trade_media"
    threat_level: ThreatLevel = "none"
    week_id: str = "2026-26"
    period_id: str = "2026-06"
    source_url: str = "manual://step1"
    source_date: str = "확인필요"
    raw_text: str = ""
    summary: str = ""
    product_or_series: str = "확인필요"
    condition_or_capacity: str = "확인필요"
    application: str = "Residential/Unitary/Heat pump"
    source_name: str = "수동 입력"
    is_primary: bool = False
    low_confidence: bool = False
    dynamic_tags: list[str] = field(default_factory=list)
    evidence_id: str = ""
    modality: str = "text"
    extraction_confidence: float = 1.0
    source_page: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data["evidence_id"]:
            data["evidence_id"] = f"{self.week_id}:{self.compressor_type}:{self.competitor}:{self.category}:{self.source_url}"
        return data


@dataclass(frozen=True)
class ThreatItem:
    compressor_type: str
    refrigerant: str
    condition: str
    competitor: str
    threat_level: Literal["high", "medium", "low"]
    trust_score: int
    evidence_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SignalItem:
    signal_type: SignalType
    description: str
    competitor: str
    trust_score: int
    week_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnalysisBundle:
    gap_matrix: dict[str, Any]
    threat_summary: list[ThreatItem]
    new_signals: list[SignalItem]
    week_id: str
    baseline_used: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_matrix": self.gap_matrix,
            "threat_summary": [item.to_dict() for item in self.threat_summary],
            "new_signals": [item.to_dict() for item in self.new_signals],
            "week_id": self.week_id,
            "baseline_used": self.baseline_used,
        }


@dataclass(frozen=True)
class ReportMetadata:
    week_id: str
    run_date: str
    total_evidence_count: int
    type_coverage: list[str]
    competitor_coverage: list[str]
    primary_missing: list[str]
    high_threat_count: int
    critic_score: int
    hard_fail: bool
    signal_count: int = 0
    period_id: str = ""

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
    query_plan: dict[str, Any]
    raw_results: dict[str, Any]
    week_id: str
    period_id: str
    report_meta: dict[str, Any] | None
    analysis_bundle: dict[str, Any] | None
    analysis_path: str
    writer_directives: list[str]
    reasoning_log: list[dict[str, str]]
    evidence_ledger_path: str
    gap_history_path: str
    critic_cot_path: str
    replan_count: int
    alerts: list[dict[str, Any]]
    run_log_path: str
    guardian_result: dict[str, Any]
    guardian_log_path: str
    auto_approve: bool
    auto_approve_result: dict[str, Any]
    auto_approve_log_path: str
    live_send_results: dict[str, Any]
    live_sender_log_path: str
    notifier_log_path: str
    notifier_outbox: str
    email_payload_path: str
    slack_payload_path: str
    obsidian_payload_path: str
    hermes_live_decision: dict[str, Any]
    dry_run: bool
