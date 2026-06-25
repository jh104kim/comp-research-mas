from pathlib import Path

from comp_research_mas.graph import run_step3
from comp_research_mas.memory_store import read_evidence_ledger, read_gap_history
from comp_research_mas.query_planner import build_query_plan, replan_query_plan


def test_replanning_expands_query_plan():
    plan = build_query_plan("2026-26")
    replanned = replan_query_plan(plan, evidence_count=2, threshold=8)
    assert replanned["replanned"] is True
    assert len(replanned["queries"]) >= len(plan["queries"])
    assert "replan_reason" in replanned


def test_step3_reasoning_memory_and_critic_cot_outputs():
    state = run_step3("2026-26")
    assert state["reasoning_log"]
    assert any(item["node"] == "analyst" for item in state["reasoning_log"])
    assert state.get("replan_count", 0) >= 1

    for key in ["evidence_ledger", "gap_history", "critic_cot"]:
        assert key in state["output_paths"]
        assert Path(state["output_paths"][key]).exists()

    ledger = read_evidence_ledger()
    history = read_gap_history()
    assert "2026-26" in ledger["weeks"]
    assert "2026-26" in history["weeks"]


def test_changed_threat_threshold_reduces_high_count():
    state = run_step3("2026-26")
    # After the stricter rule, high is restricted to trust_score=5 + 미보유.
    assert state["report_meta"]["high_threat_count"] == 4
    assert state["report_meta"]["signal_count"] == 6
