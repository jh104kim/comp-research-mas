from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .models import WorkflowState


def save_step1_outputs(state: WorkflowState, *, output_root: str | Path = "outputs") -> WorkflowState:
    today = date.today().isoformat()
    root = Path(output_root)
    report_dir = root / "reports"
    review_dir = root / "reviews"
    evidence_dir = root / "evidence"
    report_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / f"{today}_compressor_weekly.md"
    review_path = review_dir / f"{today}_critic_review.json"
    evidence_path = evidence_dir / f"{today}_evidence.json"

    report_path.write_text(state.get("draft", ""), encoding="utf-8")
    final_status = "saved" if not state.get("hard_fail") else "saved_human_review_required"
    review_payload: dict[str, Any] = {
        "score": state.get("score", 0),
        "feedback": state.get("feedback", {}),
        "iteration": state.get("iteration", 0),
        "status": final_status,
        "hard_fail": state.get("hard_fail", False),
        "error_log": state.get("error_log", []),
    }
    review_path.write_text(json.dumps(review_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    evidence_payload = {
        "evidence": state.get("evidence", []),
        "gap_table": state.get("gap_table", []),
        "sources": state.get("sources", []),
    }
    evidence_path.write_text(json.dumps(evidence_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        **state,
        "status": "saved" if not state.get("hard_fail") else "saved_human_review_required",
        "output_paths": {
            "report": str(report_path),
            "review": str(review_path),
            "evidence": str(evidence_path),
        },
    }
