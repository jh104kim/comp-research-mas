from pathlib import Path

from comp_research_mas.agents import critique_step_report, write_step_report
from comp_research_mas.analyst import build_analysis_bundle, load_gap_baseline, orchestrator_directives, analyst_threat_level
from comp_research_mas.graph import analyst_node, run_step3
from comp_research_mas.models import EvidenceItem


def test_gap_matrix_baseline_loads():
    baseline = load_gap_baseline("config/gap_matrix_baseline.yaml")
    assert baseline["Re"]["R290"]["MBP"]["samsung"] == "미보유"
    assert baseline["Sc"]["R454B"]["Variable"]["samsung"] == "미보유"


def _step3_evidence():
    return [
        EvidenceItem(compressor_type="Sc", competitor="Copeland/Emerson", refrigerant=["R454B"], category="신제품·라인업", samsung_status="미보유", trust_score=5, source_type="official", threat_level="high", week_id="2026-26", source_url="https://x/copeland", source_date="2026-06-20", raw_text="R454B Variable Scroll 삼성 미보유", product_or_series="R454B Variable", is_primary=True, dynamic_tags=["Variable"]),
        EvidenceItem(compressor_type="Re", competitor="GMCC/Midea", refrigerant=["R290"], category="신냉매·냉매전환", samsung_status="미보유", trust_score=5, source_type="official", threat_level="high", week_id="2026-26", source_url="https://x/gmcc", source_date="2026-06-20", raw_text="R290 MBP 2주 내 재등장 삼성 미보유", product_or_series="R290 MBP", is_primary=True, dynamic_tags=["MBP"]),
        EvidenceItem(compressor_type="Re", competitor="LG", refrigerant=["R290"], category="신냉매·냉매전환", samsung_status="미보유", trust_score=5, source_type="exhibition", threat_level="high", week_id="2026-26", source_url="https://x/lg", source_date="2026-06-20", raw_text="R290 MBP 삼성 미보유", product_or_series="R290 MBP", is_primary=True, dynamic_tags=["MBP"]),
    ]


def test_analysis_bundle_schema_gap_and_signals():
    bundle = build_analysis_bundle(_step3_evidence(), "2026-26")
    data = bundle.to_dict()
    assert data["baseline_used"] == "gap_matrix_baseline.yaml"
    assert data["gap_matrix"]["Sc"]["R454B"]["Variable"]["threat_level"] == "high"
    assert any(t["threat_level"] == "high" for t in data["threat_summary"])
    signal_types = {s["signal_type"] for s in data["new_signals"]}
    assert "primary_new_entry" in signal_types
    assert "multi_competitor_entry" in signal_types
    assert "new_refrigerant" in signal_types
    assert "spec_change" in signal_types


def test_analyst_threat_rules():
    assert analyst_threat_level("미보유", 5) == "high"
    assert analyst_threat_level("미보유", 3) == "medium"
    assert analyst_threat_level("대응중", 3) == "medium"
    assert analyst_threat_level("보유", 5) == "low"
    assert analyst_threat_level("확인필요", 5) == "none"


def test_orchestrator_fallback_and_directives():
    fallback = analyst_node({"evidence": [], "week_id": "2026-26"})
    assert fallback["analysis_bundle"] is None
    assert "fallback" in fallback["status"]
    bundle = build_analysis_bundle(_step3_evidence(), "2026-26")
    directives = orchestrator_directives(bundle)
    assert any("high threat" in d for d in directives)
    assert any("new_signals" in d for d in directives)


def test_writer_uses_analysis_bundle_first_and_critic_hard_fail():
    evidence = _step3_evidence()
    bundle = build_analysis_bundle(evidence, "2026-26").to_dict()
    draft = write_step_report(evidence, analysis_bundle=bundle, writer_directives=["high threat 항목을 핵심 동향 최상단에 배치"])
    assert "[ANALYSIS][high]" in draft
    assert "신규/이상 신호" in draft
    assert "R454B" in draft
    review = critique_step_report(draft, [e.to_dict() for e in evidence], analysis_bundle=bundle)
    assert review["hard_fail"] is False
    bad = critique_step_report("# bad\n## 출처 목록\nhttps://x", [e.to_dict() for e in evidence], analysis_bundle=bundle)
    assert bad["hard_fail"] is True
    assert any("Gap Matrix" in reason or "high threat" in reason for reason in bad["hard_fail_reasons"])


def test_step3_graph_e2e_outputs_analysis():
    state = run_step3("2026-26")
    assert state["status"] == "saved"
    assert state["score"] >= 7
    assert state["hard_fail"] is False
    assert state["analysis_bundle"]
    assert state["report_meta"]["signal_count"] > 0
    assert state["report_meta"]["high_threat_count"] > 0
    assert Path(state["output_paths"]["analysis"]).exists()
