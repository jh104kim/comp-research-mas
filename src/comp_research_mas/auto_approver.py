from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AutoApproveResult:
    approve: bool
    score: int
    reasons: list[str] = field(default_factory=list)
    audit_log: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_auto_approve(state: dict[str, Any]) -> AutoApproveResult:
    score = int(state.get("score", 0))
    hard_fail = bool(state.get("hard_fail", False))
    guardian = state.get("guardian_result") or {}
    guardian_severity = guardian.get("severity", "pass")
    reasons: list[str] = []
    if score < 9:
        reasons.append(f"critic_score < 9 ({score})")
    if hard_fail:
        reasons.append("hard_fail = True")
    if guardian_severity != "pass":
        reasons.append(f"guardian != pass ({guardian_severity})")
    approve = not reasons
    audit_log = {
        "period_id": state.get("period_id", "unknown"),
        "score": score,
        "hard_fail": hard_fail,
        "guardian_severity": guardian_severity,
        "approve": approve,
        "reasons": reasons,
        "conditions": {"critic_score>=9": score >= 9, "hard_fail=False": not hard_fail, "guardian=pass": guardian_severity == "pass"},
    }
    return AutoApproveResult(approve=approve, score=score, reasons=reasons, audit_log=audit_log)


def write_auto_approve_log(result: AutoApproveResult, period_id: str) -> Path:
    path = Path("outputs/logs") / f"{period_id}_auto_approve.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def auto_approver_node(state: dict[str, Any]) -> dict[str, Any]:
    period_id = state.get("period_id", "unknown")
    result = evaluate_auto_approve(state)
    log_path = write_auto_approve_log(result, period_id)
    from .workflow_utils import append_reasoning
    reasoning_log = append_reasoning(
        state,
        node="auto_approver",
        step="자동 승인 판단",
        judgment="auto_approve" if result.approve else "manual_review_required",
        reasoning="critic_score>=9, hard_fail=False, guardian=pass 조건을 평가",
        tool_used=True,
        rag_used=False,
        conclusion="approve=True" if result.approve else "; ".join(result.reasons),
    )
    return {
        **state,
        "auto_approve": result.approve,
        "auto_approve_result": result.to_dict(),
        "auto_approve_log_path": str(log_path),
        "human_review_flag": not result.approve,
        "auto_publish_blocked": not result.approve,
        "reasoning_log": reasoning_log,
        "output_paths": {**state.get("output_paths", {}), "auto_approve": str(log_path)},
    }
