from comp_research_mas.evidence_normalizer import normalize_raw_results, threat_level, trust_score
from comp_research_mas.graph import run_step2
from comp_research_mas.models import PRIMARY_COMPETITORS
from comp_research_mas.query_planner import build_query_plan


def test_query_planner_has_type_coverage_and_primary_queries():
    plan = build_query_plan("2026-26")
    queries = plan["queries"]
    assert {q["compressor_type"] for q in queries} == {"Re", "Ro", "Sc"}
    for ctype, competitors in PRIMARY_COMPETITORS.items():
        for competitor in competitors:
            assert any(q["compressor_type"] == ctype and q["competitor"] == competitor and q["priority"] == "primary" for q in queries)


def test_evidence_normalizer_alias_trust_threat_and_dedup():
    raw = {
        "week_id": "2026-26",
        "results": [
            {"compressor_type": "Sc", "competitor": "Emerson", "category": "신제품·라인업", "refrigerants": ["R454B"], "source_type": "official", "source_url": "https://a", "source_date": "2026-06-20", "title": "ZO", "summary": "new", "raw_text": "삼성 미보유", "samsung_status": "미보유"},
            {"compressor_type": "Sc", "competitor": "Copeland", "category": "신제품·라인업", "refrigerants": ["R454B"], "source_type": "news", "source_url": "https://b", "source_date": "2026-06-20", "title": "ZO dup", "summary": "dup", "raw_text": "삼성 미보유", "samsung_status": "미보유"},
        ],
    }
    items = normalize_raw_results(raw)
    assert len(items) == 1
    item = items[0]
    assert item.competitor == "Copeland/Emerson"
    assert item.trust_score == 5
    assert item.threat_level == "high"
    assert item.refrigerant == ["R454B"]
    assert item.source_type == "official"


def test_trust_and_threat_rules():
    assert trust_score("official") == 5
    assert trust_score("academic") == 4
    assert trust_score("trade_media") == 3
    assert threat_level("미보유", 5) == "high"
    assert threat_level("미보유", 3) == "medium"
    assert threat_level("대응중", 3) == "medium"
    assert threat_level("보유", 5) == "low"
    assert threat_level("확인필요", 5) == "none"


def test_step2_graph_e2e_outputs_metadata():
    state = run_step2("2026-26")
    assert state["status"] == "saved"
    assert state["score"] >= 7
    assert state["report_meta"]["week_id"] == "2026-26"
    assert state["report_meta"]["total_evidence_count"] > 0
    assert set(state["report_meta"]["type_coverage"]) == {"Re", "Ro", "Sc"}
    assert "query_plan" in state
    assert "raw_results" in state
    assert state["output_paths"]["report"]
