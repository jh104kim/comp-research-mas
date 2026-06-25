from comp_research_mas.agents import critique_step_report, critic_node, write_step_report
from comp_research_mas.models import EvidenceItem


def _evidence(high_trust: bool = True):
    source_type = "official" if high_trust else "news"
    trust = 5 if high_trust else 2
    return [
        EvidenceItem(compressor_type="Re", competitor="GMCC/Midea", refrigerant=["R290"], category="신냉매·냉매전환", samsung_status="미보유", trust_score=trust, source_type=source_type, threat_level="high", source_url="https://x/gmcc-re", raw_text="GMCC Re R290 삼성 미보유", is_primary=True),
        EvidenceItem(compressor_type="Re", competitor="LG", refrigerant=["R290"], category="신냉매·냉매전환", samsung_status="미보유", trust_score=trust, source_type=source_type, threat_level="high", source_url="https://x/lg-re", raw_text="LG Re R290 삼성 미보유", is_primary=True),
        EvidenceItem(compressor_type="Ro", competitor="GMCC/Midea", refrigerant=["R32"], category="신제품·라인업", samsung_status="확인필요", trust_score=trust, source_type=source_type, threat_level="none", source_url="https://x/gmcc-ro", raw_text="GMCC Ro R32 확인 필요", is_primary=True),
        EvidenceItem(compressor_type="Ro", competitor="LG", refrigerant=["R32"], category="신제품·라인업", samsung_status="확인필요", trust_score=trust, source_type=source_type, threat_level="none", source_url="https://x/lg-ro", raw_text="LG Ro R32 확인 필요", is_primary=True),
        EvidenceItem(compressor_type="Sc", competitor="Copeland/Emerson", refrigerant=["R454B"], category="신제품·라인업", samsung_status="대응중", trust_score=trust, source_type=source_type, threat_level="medium", source_url="https://x/copeland-1", raw_text="Copeland Sc R454B 삼성 대응 중", is_primary=True),
        EvidenceItem(compressor_type="Sc", competitor="Copeland/Emerson", refrigerant=["R32"], category="성능·효율", samsung_status="대응중", trust_score=trust, source_type=source_type, threat_level="medium", source_url="https://x/copeland-2", raw_text="Copeland Sc R32 삼성 대응 중", is_primary=True),
    ]


def test_critic_rubric_full_score_and_breakdown():
    ev = _evidence()
    draft = write_step_report(ev)
    review = critique_step_report(draft, [e.to_dict() for e in ev])
    assert review["score"] == 10
    assert review["rubric_breakdown"] == {
        "structure": 2,
        "samsung_comparison": 3,
        "gap_matrix": 2,
        "evidence": 1,
        "source_trust": 1,
        "primary_competitor_coverage": 1,
    }


def test_critic_rubric_zero_cases_for_missing_evidence_and_low_trust():
    ev = _evidence(high_trust=False)[:2]
    draft = "# bad\n## Re\n### 신제품·라인업\n## 출처 목록\nhttps://x"
    review = critique_step_report(draft, [e.to_dict() for e in ev])
    assert review["rubric_breakdown"]["evidence"] == 0
    assert review["rubric_breakdown"]["source_trust"] == 0
    assert review["score"] < 7
    assert review["debate_points"]
    assert all(point["severity"] == "major" for point in review["debate_points"])


def test_critic_generates_directives_and_no_improvement_human_review():
    ev = _evidence()[:2]
    state = {"draft": "# bad", "evidence": [e.to_dict() for e in ev], "iteration": 1, "score": 5, "error_log": [], "reasoning_log": []}
    reviewed = critic_node(state)
    assert reviewed["human_review_flag"] is True
    assert reviewed["hard_fail"] is True
    assert any("재작성 후 score 개선 없음" in reason for reason in reviewed["error_log"])
    assert reviewed["writer_directives"]
