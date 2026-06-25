from pathlib import Path

from comp_research_mas.agents import critique_step1_report, write_step1_report
from comp_research_mas.graph import run_step1
from comp_research_mas.models import CATEGORIES, PRIMARY_COMPETITORS, EvidenceItem
from comp_research_mas.tools import parse_step1_raw_data


def test_step1_parser_marks_primary_competitors():
    raw = Path("examples/manual_search_results/step1_raw_data.md").read_text(encoding="utf-8")
    evidence = parse_step1_raw_data(raw)
    assert len(evidence) == 9
    primaries = {(item.compressor_type, item.competitor) for item in evidence if item.is_primary}
    assert ("Re", "GMCC/Midea") in primaries
    assert ("Re", "LG") in primaries
    assert ("Ro", "GMCC/Midea") in primaries
    assert ("Ro", "LG") in primaries
    assert ("Sc", "Copeland/Emerson") in primaries
    gmcc_re = next(item for item in evidence if item.compressor_type == "Re" and item.competitor == "GMCC/Midea")
    assert gmcc_re.samsung_status == "미보유"


def test_writer_includes_primary_competitors_even_without_evidence():
    evidence = [
        EvidenceItem(
            compressor_type="Re",
            competitor="GMCC/Midea",
            summary="PA90 R290 신모델. 삼성 R290 LBP Re: 미보유",
            samsung_status="미보유",
            is_primary=True,
            source_name="manual",
            source_date="2026-06-25",
        )
    ]
    draft = write_step1_report(evidence)
    for ctype, competitors in PRIMARY_COMPETITORS.items():
        assert f"## {ctype}" in draft
        for competitor in competitors:
            assert f"#### {competitor}" in draft
    assert "해당 없음 — 이번 주 확인된 고신뢰 근거 없음" in draft


def test_critic_scores_and_hard_fail():
    raw = Path("examples/manual_search_results/step1_raw_data.md").read_text(encoding="utf-8")
    evidence = parse_step1_raw_data(raw)
    draft = write_step1_report(evidence)
    review = critique_step1_report(draft, [item.to_dict() for item in evidence])
    assert review["score"] >= 7
    assert review["hard_fail"] is False

    bad = critique_step1_report("# bad", [])
    assert bad["hard_fail"] is True
    assert "출처 0개" in bad["hard_fail_reasons"]


def test_step1_langgraph_e2e_creates_outputs():
    raw = Path("examples/manual_search_results/step1_raw_data.md").read_text(encoding="utf-8")
    state = run_step1(raw)
    assert state["score"] >= 7
    assert state["hard_fail"] is False
    assert state["status"] == "saved"
    paths = state["output_paths"]
    assert Path(paths["report"]).exists()
    assert Path(paths["review"]).exists()
    assert Path(paths["evidence"]).exists()
    report = Path(paths["report"]).read_text(encoding="utf-8")
    for ctype in ("Re", "Ro", "Sc"):
        assert f"## {ctype}" in report
    for category in CATEGORIES:
        assert f"### {category}" in report
