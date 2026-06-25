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
    report_path = report_dir / f"{today}_compressor_weekly.md"
    review_path = review_dir / f"{today}_critic_review.json"
    evidence_path = evidence_dir / f"{week_id}_evidence.json"

    final_status = "saved" if not state.get("hard_fail") else "saved_human_review_required"
    meta = build_report_metadata({**state, "run_date": today, "status": final_status})
    state = {**state, "report_meta": meta.to_dict()}

    report_path.write_text(state.get("draft", ""), encoding="utf-8")
    review_payload: dict[str, Any] = {"score": state.get("score", 0), "feedback": state.get("feedback", {}), "iteration": state.get("iteration", 0), "status": final_status, "hard_fail": state.get("hard_fail", False), "error_log": state.get("error_log", []), "writer_directives": state.get("writer_directives", []), "analysis_path": state.get("analysis_path"), "report_meta": state.get("report_meta")}
    review_path.write_text(json.dumps(review_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    evidence_payload = {"week_id": week_id, "evidence": state.get("evidence", []), "gap_table": state.get("gap_table", []), "sources": state.get("sources", []), "report_meta": state.get("report_meta")}
    evidence_path.write_text(json.dumps(evidence_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    output_paths = {"report": str(report_path), "review": str(review_path), "evidence": str(evidence_path)}
    if state.get("analysis_path"):
        output_paths["analysis"] = str(state["analysis_path"])
    return {**state, "status": final_status, "output_paths": output_paths}


def save_step1_outputs(state: WorkflowState, *, output_root: str | Path = "outputs") -> WorkflowState:
    return save_step_outputs(state, output_root=output_root)
