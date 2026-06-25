from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .alert import emit_alert
from .workflow_utils import append_reasoning

BLOCK_PATTERNS = [
    r"sk-[A-Za-z0-9]",
    r"ghp_|github_pat_",
    r"BEGIN PRIVATE KEY",
    r"삼성.*원가",
    r"삼성.*미공개",
    r"samsung.*internal",
]
WARN_PATTERNS = [r"confidential", r"내부자료", r"비공개", r"사내"]


@dataclass(frozen=True)
class GuardianResult:
    passed: bool
    block_hits: list[str] = field(default_factory=list)
    warn_hits: list[str] = field(default_factory=list)
    scanned_fields: list[str] = field(default_factory=list)
    severity: str = "pass"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hits(patterns: list[str], text: str) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            found.append(pattern)
    return found


def scan_text(text: str) -> GuardianResult:
    block = _hits(BLOCK_PATTERNS, text)
    warn = _hits(WARN_PATTERNS, text)
    severity = "block" if block else "warn" if warn else "pass"
    return GuardianResult(passed=not block and not warn, block_hits=block, warn_hits=warn, scanned_fields=["text"], severity=severity)


def scan_state(state: dict[str, Any]) -> GuardianResult:
    fields = ["raw_results", "evidence", "draft", "feedback", "analysis_bundle", "output_paths"]
    text_parts: list[str] = []
    scanned: list[str] = []
    for field_name in fields:
        if field_name in state:
            scanned.append(field_name)
            text_parts.append(json.dumps(state.get(field_name), ensure_ascii=False, default=str))
    result = scan_text("\n".join(text_parts))
    return GuardianResult(result.passed, result.block_hits, result.warn_hits, scanned, result.severity)


def write_guardian_log(result: GuardianResult, period_id: str) -> Path:
    path = Path("outputs/logs") / f"{period_id}_guardian.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def guardian_node(state: dict[str, Any]) -> dict[str, Any]:
    period_id = state.get("period_id", state.get("week_id", "unknown"))
    result = scan_state(state)
    log_path = write_guardian_log(result, period_id)
    alerts = list(state.get("alerts", []))
    if result.severity == "block":
        alerts.append(emit_alert("guardian_block", "Guardian block 패턴 감지", period_id=period_id, payload=result.to_dict()))
    elif result.severity == "warn":
        alerts.append(emit_alert("guardian_warn", "Guardian warn 패턴 감지", period_id=period_id, payload=result.to_dict()))
    reasoning_log = append_reasoning(
        state,
        node="guardian",
        step="보안·정책 감시",
        judgment=result.severity,
        reasoning="block/warn/pass 패턴 기반 scan_state 수행" if result.severity != "pass" else "민감정보 패턴 없음",
        tool_used=True,
        rag_used=False,
        persona_role="MAS 보안·정책 감시 에이전트",
        conclusion=f"severity={result.severity}",
    )
    next_state = {
        **state,
        "guardian_result": result.to_dict(),
        "guardian_log_path": str(log_path),
        "reasoning_log": reasoning_log,
        "alerts": alerts,
        "output_paths": {**state.get("output_paths", {}), "guardian": str(log_path)},
    }
    if result.severity == "block":
        next_state.update({"hard_fail": True, "human_review_flag": True, "auto_publish_blocked": True, "status": "guardian_blocked"})
    elif result.severity == "warn":
        next_state.update({"human_review_flag": True, "auto_publish_blocked": True, "status": "guardian_warn"})
    return next_state
