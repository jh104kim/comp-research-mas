from comp_research_mas.agents import (
    EVIDENCE_THRESHOLD,
    critique_step_report,
    critic_node,
    get_period_context,
    write_step_report,
)
from comp_research_mas.models import EvidenceItem


def _evidence(high_trust: bool = True, period_id: str = "2026-06"):
    source_type = "official" if high_trust else "news"
    trust = 5 if high_trust else 2
    return [
        EvidenceItem(compressor_type="Re", competitor="GMCC/Midea", refrigerant=["R290"], category="신냉매·냉매전환", samsung_status="미보유", trust_score=trust, source_type=source_type, threat_level="high", source_url="https://x/gmcc-re", raw_text="GMCC Re R290 삼성 미보유", is_primary=True, period_id=period_id),
        EvidenceItem(compressor_type="Re", competitor="LG", refrigerant=["R290"], category="신냉매·냉매전환", samsung_status="미보유", trust_score=trust, source_type=source_type, threat_level="high", source_url="https://x/lg-re", raw_text="LG Re R290 삼성 미보유", is_primary=True, period_id=period_id),
        EvidenceItem(compressor_type="Ro", competitor="GMCC/Midea", refrigerant=["R32"], category="신제품·라인업", samsung_status="확인필요", trust_score=trust, source_type=source_type, threat_level="none", source_url="https://x/gmcc-ro", raw_text="GMCC Ro R32 확인 필요", is_primary=True, period_id=period_id),
        EvidenceItem(compressor_type="Ro", competitor="LG", refrigerant=["R32"], category="신제품·라인업", samsung_status="확인필요", trust_score=trust, source_type=source_type, threat_level="none", source_url="https://x/lg-ro", raw_text="LG Ro R32 확인 필요", is_primary=True, period_id=period_id),
        EvidenceItem(compressor_type="Sc", competitor="Copeland/Emerson", refrigerant=["R454B"], category="신제품·라인업", samsung_status="대응중", trust_score=trust, source_type=source_type, threat_level="medium", source_url="https://x/copeland-1", raw_text="Copeland Sc R454B 삼성 대응 중", is_primary=True, period_id=period_id),
        EvidenceItem(compressor_type="Sc", competitor="Copeland/Emerson", refrigerant=["R32"], category="성능·효율", samsung_status="대응중", trust_score=trust, source_type=source_type, threat_level="medium", source_url="https://x/copeland-2", raw_text="Copeland Sc R32 삼성 대응 중", is_primary=True, period_id=period_id),
    ]


def test_period_context_and_thresholds():
    assert get_period_context("2026-01") == "exhibition"
    assert get_period_context("2026-04") == "exhibition"
    assert get_period_context("2026-10") == "exhibition"
    assert get_period_context("2025-10") == "exhibition"
    assert get_period_context("2025-11") == "backfill"
    assert get_period_context("2026-06") == "normal"
    assert EVIDENCE_THRESHOLD == {"exhibition": 8, "backfill": 4, "normal": 6}


def test_critic_rubric_full_score_and_breakdown():
    ev = _evidence(period_id="2026-06")
    draft = write_step_report(ev)
    review = critique_step_report(draft, [e.to_dict() for e in ev])
    assert review["score"] == 10
    breakdown = review["rubric_breakdown"]
    assert breakdown["structure"] == 2
    assert breakdown["samsung_comparison"] == 3
    assert breakdown["gap_matrix"] == 2
    assert breakdown["evidence_volume"] == 1
    assert breakdown["primary_type_coverage"] == 1
    assert breakdown["source_trust"] == 1
    assert breakdown["period_context"] == "normal"
    assert breakdown["evidence_threshold_used"] == 6
    assert breakdown["total"] == 10


def test_dynamic_evidence_threshold_exhibition_backfill_normal():
    normal = critique_step_report(write_step_report(_evidence(period_id="2026-06")[:3]), [e.to_dict() for e in _evidence(period_id="2026-06")[:3]])
    assert normal["rubric_breakdown"]["period_context"] == "normal"
    assert normal["rubric_breakdown"]["evidence_threshold_used"] == 6
    assert normal["rubric_breakdown"]["evidence_volume"] == 0.5
    assert normal["low_confidence"] is True

    exhibition = critique_step_report(write_step_report(_evidence(period_id="2026-01")[:4]), [e.to_dict() for e in _evidence(period_id="2026-01")[:4]])
    assert exhibition["rubric_breakdown"]["period_context"] == "exhibition"
    assert exhibition["rubric_breakdown"]["evidence_threshold_used"] == 8
    assert exhibition["rubric_breakdown"]["evidence_volume"] == 0.5

    backfill = critique_step_report(write_step_report(_evidence(period_id="2025-11")[:4]), [e.to_dict() for e in _evidence(period_id="2025-11")[:4]])
    assert backfill["rubric_breakdown"]["period_context"] == "backfill"
    assert backfill["rubric_breakdown"]["evidence_threshold_used"] == 4
    assert backfill["rubric_breakdown"]["evidence_volume"] == 1


def test_primary_type_coverage_partial_and_missing():
    partial_ev = [e for e in _evidence() if e.compressor_type in {"Re", "Ro"}]
    partial = critique_step_report(write_step_report(partial_ev), [e.to_dict() for e in partial_ev])
    assert partial["rubric_breakdown"]["primary_type_coverage"] == 0.5
    assert partial["low_confidence"] is True

    missing_ev = [EvidenceItem(compressor_type="Re", competitor="Secop", refrigerant=["R290"], source_url="https://x/secop", raw_text="Secop", period_id="2026-06")]
    missing = critique_step_report(write_step_report(missing_ev), [e.to_dict() for e in missing_ev])
    assert missing["rubric_breakdown"]["primary_type_coverage"] == 0


def test_evidence_shortage_does_not_hard_fail_when_report_structure_exists():
    ev = _evidence()[:3]
    draft = write_step_report(ev)
    review = critique_step_report(draft, [e.to_dict() for e in ev])
    assert review["rubric_breakdown"]["evidence_volume"] == 0.5
    assert review["low_confidence"] is True
    assert review["hard_fail"] is False
    assert any("재검색 권장" in d for d in review["writer_directives"])


def test_low_trust_source_score_half_and_zero():
    one_high = _evidence(high_trust=True)[:1] + _evidence(high_trust=False)[1:4]
    review = critique_step_report(write_step_report(one_high), [e.to_dict() for e in one_high])
    assert review["rubric_breakdown"]["source_trust"] == 0.5

    low = _evidence(high_trust=False)[:4]
    low_review = critique_step_report(write_step_report(low), [e.to_dict() for e in low])
    assert low_review["rubric_breakdown"]["source_trust"] == 0


def test_critic_generates_directives_and_no_improvement_human_review():
    ev = _evidence()[:2]
    state = {"draft": "# bad", "evidence": [e.to_dict() for e in ev], "iteration": 1, "score": 5, "error_log": [], "reasoning_log": []}
    reviewed = critic_node(state)
    assert reviewed["human_review_flag"] is True
    assert reviewed["hard_fail"] is True
    assert any("재작성 후 score 개선 없음" in reason for reason in reviewed["error_log"])
    assert reviewed["writer_directives"]
