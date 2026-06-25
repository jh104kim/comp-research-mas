from pathlib import Path
import json

from comp_research_mas.backfill_planner import build_backfill_plan, boosted_sources_for_period, run_backfill


def test_backfill_plan_period_keywords_and_exhibition_boosts():
    plan = build_backfill_plan(["2025-10", "2026-01", "2026-04"])
    assert plan["period_count"] == 3
    assert "Chillventa" in boosted_sources_for_period("2025-10")
    assert "AHR Expo" in boosted_sources_for_period("2026-01")
    assert "China Refrigeration Expo" in boosted_sources_for_period("2026-04")
    first_query = plan["periods"][0]["query_plan"]["queries"][0]
    assert first_query["date_range"] == {"from": "2025-10-01", "to": "2025-10-31"}
    assert any("2025-10" in kw or "2025 Q4" in kw for kw in first_query["keywords"])


def test_run_backfill_dry_run_outputs_latest_and_quality_tags():
    summary = run_backfill(from_period="2025-07", to_period="2025-08", dry_run=True)
    assert summary["period_count"] == 2
    assert summary["latest"]["period_id"] == "2025-08"
    assert "gap_matrix" in summary["latest"]
    assert all(snap["data_insufficient"] for snap in summary["period_snapshots"])
    path = Path(summary["output_paths"]["backfill_gap_summary"])
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "period_snapshots" in data
    assert "latest" in data
    assert "state_changes" in data
    ledger = Path(summary["output_paths"]["evidence_ledger"])
    assert ledger.exists()
    ledger_data = json.loads(ledger.read_text(encoding="utf-8"))
    assert "2025-07" in ledger_data["periods"]
    sample = ledger_data["periods"]["2025-07"]["evidence"][0]
    assert sample["period_evidence_quality"] == "data_insufficient"
    assert "데이터 부족" in sample["dynamic_tags"]
