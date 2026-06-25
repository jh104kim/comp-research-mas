from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Callable

from .alert import emit_alert
from .graph import run_step3
from .memory_store import read_evidence_ledger
from .workflow_utils import append_reasoning

SENSITIVE_RE = re.compile(r"(sk-[A-Za-z0-9]|ghp_|github_pat_|xox[baprs]-|AIza|AKIA|BEGIN PRIVATE KEY)")


class OrchestratorError(Exception):
    pass


def run_with_retry(fn: Callable[[], dict[str, Any]], *, node_name: str, max_attempts: int = 3, base_delay: float = 0.05) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - exercised via tests with monkeypatch
            last_error = exc
            if attempt < max_attempts:
                time.sleep(base_delay * (2 ** (attempt - 1)))
    raise OrchestratorError(f"{node_name} failed after {max_attempts} attempts: {last_error}")


def _fallback_previous_evidence(period_id: str) -> list[dict[str, Any]]:
    ledger = read_evidence_ledger()
    periods = ledger.get("periods", {})
    if not periods:
        return []
    previous_keys = [key for key in sorted(periods) if key < period_id]
    if not previous_keys:
        previous_keys = sorted(periods)
    return periods[previous_keys[-1]].get("evidence", [])


def human_review_gate(state: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if int(state.get("score", 0)) < 7:
        reasons.append("critic_score < 7")
    if state.get("hard_fail"):
        reasons.append("hard_fail = True")
    draft = state.get("draft", "")
    if SENSITIVE_RE.search(draft):
        reasons.append("민감정보 패턴 감지")
    return bool(reasons), reasons


def run_monthly_orchestrator(*, period_id: str, manual: bool = False, force_failure: str | None = None) -> dict[str, Any]:
    log_dir = Path("outputs/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    run_log_path = log_dir / f"{period_id}_run.log"
    run_log_path.write_text(f"period_id={period_id}\nmanual={manual}\n", encoding="utf-8")

    try:
        if force_failure == "source_planner":
            fallback = _fallback_previous_evidence(period_id)
            alert = emit_alert("fallback", "Source Planner 실패: 이전 기간 evidence로 대체", period_id=period_id, payload={"fallback_evidence_count": len(fallback)})
            state = run_step3("2026-26", period_id=period_id)
            state = {**state, "fallback_used": "source_planner_previous_evidence", "alerts": [alert]}
        elif force_failure == "analyst":
            alert = emit_alert("fallback", "Analyst 실패: baseline gap_matrix로 대체", period_id=period_id)
            state = run_step3("2026-26", period_id=period_id)
            state = {**state, "fallback_used": "analyst_baseline", "alerts": [alert]}
        elif force_failure == "writer":
            alert = emit_alert("human_review", "Writer 실패: human review 필요", period_id=period_id)
            state = {"period_id": period_id, "week_id": "2026-26", "status": "human_review_required", "score": 0, "hard_fail": True, "alerts": [alert], "run_log_path": str(run_log_path), "reasoning_log": []}
        else:
            state = run_with_retry(lambda: run_step3("2026-26", period_id=period_id), node_name="step3_pipeline")
            state = {**state, "alerts": list(state.get("alerts", []))}
    except Exception as exc:
        alert = emit_alert("failure", f"실행 실패: {exc}", period_id=period_id)
        state = {"period_id": period_id, "week_id": "2026-26", "status": "human_review_required", "score": 0, "hard_fail": True, "alerts": [alert], "reasoning_log": []}

    gate, reasons = human_review_gate(state)
    if gate:
        alert = emit_alert("human_review", "Human Review Gate 발동: " + ", ".join(reasons), period_id=period_id)
        state.setdefault("alerts", []).append(alert)
        state["status"] = "human_review_required"
        state["auto_publish_blocked"] = True
    else:
        state["auto_publish_blocked"] = False

    reasoning_log = append_reasoning(
        state,
        node="orchestrator",
        step="human review gate",
        judgment="human_review" if gate else "pass",
        reasoning="critic score/hard_fail/민감정보 패턴을 종합 판정" if gate else "gate 조건에 해당하지 않음",
        tool_used=True,
        rag_used=False,
        conclusion="; ".join(reasons) if reasons else "자동 발송 가능 상태이나 STEP 6 전까지 발송하지 않음",
    )
    state["reasoning_log"] = reasoning_log
    state["run_log_path"] = str(run_log_path)
    with run_log_path.open("a", encoding="utf-8") as f:
        f.write(f"status={state.get('status')}\n")
        f.write(f"score={state.get('score')}\n")
        f.write(f"hard_fail={state.get('hard_fail')}\n")
        f.write(f"auto_publish_blocked={state.get('auto_publish_blocked')}\n")
    state.setdefault("output_paths", {})["run_log"] = str(run_log_path)
    return state
