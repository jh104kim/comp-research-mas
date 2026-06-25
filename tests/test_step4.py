from datetime import date
from pathlib import Path

from comp_research_mas.memory_store import append_evidence_ledger, append_gap_history, get_gap_status_change, get_previous_period_evidence, read_evidence_ledger, read_gap_history
from comp_research_mas.orchestrator import human_review_gate, run_monthly_orchestrator
from comp_research_mas.scheduler import first_monday, is_monthly_run_day, period_id_for, run_monthly


def test_scheduler_monthly_first_monday_and_manual_trigger():
    assert first_monday(2026, 6) == date(2026, 6, 1)
    assert is_monthly_run_day(date(2026, 6, 1)) is True
    assert is_monthly_run_day(date(2026, 6, 2)) is False
    assert period_id_for(date(2026, 6, 25)) == "2026-06"
    skipped = run_monthly(period_id="2026-06", manual=False, today=date(2026, 6, 2))
    assert skipped["status"] == "skipped"


def test_orchestrator_step4_sample_outputs_and_judgment_log():
    state = run_monthly_orchestrator(period_id="2026-06", manual=True)
    assert state["status"] == "saved"
    assert state["period_id"] == "2026-06"
    assert state["auto_publish_blocked"] is False
    assert Path(state["output_paths"]["run_log"]).exists()
    assert state["reasoning_log"]
    assert all("judgment" in item for item in state["reasoning_log"])
    assert any(item["node"] == "orchestrator" for item in state["reasoning_log"])


def test_orchestrator_fallback_and_human_review_gate():
    state = run_monthly_orchestrator(period_id="2026-07", manual=True, force_failure="writer")
    assert state["status"] == "human_review_required"
    assert state["auto_publish_blocked"] is True
    assert state["alerts"]
    gate, reasons = human_review_gate({"score": 6, "hard_fail": False, "draft": "safe"})
    assert gate is True
    assert "critic_score < 7" in reasons


def test_period_memory_store_previous_lookup_and_status_change():
    append_evidence_ledger("2026-22", [{"competitor": "GMCC/Midea", "category": "신제품·라인업", "value": "prev"}], period_id="2026-05")
    previous = get_previous_period_evidence("GMCC/Midea", "신제품·라인업", "2026-06")
    assert previous and previous[0]["value"] == "prev"

    append_gap_history("2026-22", {"gap_matrix": {"Re": {"R290": {"MBP": {"samsung_status": "미보유"}}}}}, period_id="2026-05")
    append_gap_history("2026-26", {"gap_matrix": {"Re": {"R290": {"MBP": {"samsung_status": "대응중"}}}}}, period_id="2026-06")
    change = get_gap_status_change("Re", "R290", "MBP", "2026-06")
    assert change == {"from": "미보유", "to": "대응중", "period_id": "2026-06", "previous_period_id": "2026-05"}


def test_human_review_gate_sensitive_pattern():
    gate, reasons = human_review_gate({"score": 10, "hard_fail": False, "draft": "contains sk-abcdef"})
    assert gate is True
    assert "민감정보 패턴 감지" in reasons
