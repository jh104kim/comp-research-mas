from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .agents import build_report_metadata
from .models import WorkflowState


def save_step_outputs(state: WorkflowState, *, output_root: str | Path = "outputs") -> WorkflowState:
    today = date.today().isoformat()
    root = Path(output_root)
    report_dir = root / "reports"
    review_dir = root / "reviews"
    evidence_dir = root / "evidence"
    for directory in (report_dir, review_dir, evidence_dir):
        directory.mkdir(parents=True, exist_ok=True)

    week_id = state.get("week_id", "unknown")
    period_id = state.get("period_id")
    if period_id and len(str(period_id)) == 7:
        report_path = report_dir / f"{period_id}_compressor_monthly.md"
        review_path = review_dir / f"{period_id}_critic_review.json"
        critic_cot_path = review_dir / f"{period_id}_critic_cot.json"
        evidence_path = evidence_dir / f"{period_id}_evidence.json"
    else:
        report_path = report_dir / f"{today}_compressor_weekly.md"
        review_path = review_dir / f"{today}_critic_review.json"
        critic_cot_path = review_dir / f"{today}_critic_cot.json"
        evidence_path = evidence_dir / f"{week_id}_evidence.json"

    final_status = "saved" if not state.get("hard_fail") else "saved_human_review_required"
    meta = build_report_metadata({**state, "run_date": today, "status": final_status})
    state = {**state, "report_meta": meta.to_dict(), "critic_cot_path": str(critic_cot_path)}

    report_path.write_text(state.get("draft", ""), encoding="utf-8")
    review_payload: dict[str, Any] = {
        "score": state.get("score", 0),
        "feedback": state.get("feedback", {}),
        "iteration": state.get("iteration", 0),
        "status": final_status,
        "hard_fail": state.get("hard_fail", False),
        "error_log": state.get("error_log", []),
        "writer_directives": state.get("writer_directives", []),
        "analysis_path": state.get("analysis_path"),
        "evidence_ledger_path": state.get("evidence_ledger_path"),
        "gap_history_path": state.get("gap_history_path"),
        "critic_cot_path": str(critic_cot_path),
        "reasoning_log_count": len(state.get("reasoning_log", [])),
        "report_meta": state.get("report_meta"),
    }
    review_path.write_text(json.dumps(review_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    critic_cot_payload = {
        "week_id": week_id,
        "period_id": state.get("period_id", week_id),
        "score": state.get("score", 0),
        "feedback": state.get("feedback", {}),
        "reasoning_log": state.get("reasoning_log", []),
    }
    critic_cot_path.write_text(json.dumps(critic_cot_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    evidence_payload = {"week_id": week_id, "period_id": state.get("period_id", week_id), "evidence": state.get("evidence", []), "gap_table": state.get("gap_table", []), "sources": state.get("sources", []), "report_meta": state.get("report_meta")}
    evidence_path.write_text(json.dumps(evidence_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    output_paths = dict(state.get("output_paths", {}))
    output_paths.update({"report": str(report_path), "review": str(review_path), "critic_cot": str(critic_cot_path), "evidence": str(evidence_path)})
    if state.get("analysis_path"):
        output_paths["analysis"] = str(state["analysis_path"])
    if state.get("evidence_ledger_path"):
        output_paths["evidence_ledger"] = str(state["evidence_ledger_path"])
    if state.get("gap_history_path"):
        output_paths["gap_history"] = str(state["gap_history_path"])
    if state.get("guardian_log_path"):
        output_paths["guardian"] = str(state["guardian_log_path"])
    if state.get("notifier_log_path"):
        output_paths["notifier_dry_run"] = str(state["notifier_log_path"])
    if state.get("email_payload_path"):
        output_paths["email_payload"] = str(state["email_payload_path"])
    if state.get("slack_payload_path"):
        output_paths["slack_payload"] = str(state["slack_payload_path"])
    if state.get("obsidian_payload_path"):
        output_paths["obsidian_payload"] = str(state["obsidian_payload_path"])
    if state.get("auto_approve_log_path"):
        output_paths["auto_approve"] = str(state["auto_approve_log_path"])
    if state.get("live_sender_log_path"):
        output_paths["live_sender"] = str(state["live_sender_log_path"])
    return {**state, "status": final_status, "auto_publish_blocked": bool(state.get("auto_publish_blocked", False)), "output_paths": output_paths}


def save_step1_outputs(state: WorkflowState, *, output_root: str | Path = "outputs") -> WorkflowState:
    return save_step_outputs(state, output_root=output_root)
