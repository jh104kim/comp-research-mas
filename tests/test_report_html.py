import json
from pathlib import Path

from comp_research_mas.graph import run_step6
from comp_research_mas.live_sender import build_live_payloads
from comp_research_mas.report_html import build_backfill_html, markdown_to_html
from comp_research_mas.config import flatten_source_whitelist
from comp_research_mas.models import CATEGORIES


def _sample_state():
    evidence = [
        {"compressor_type": "Re", "competitor": "GMCC/Midea", "category": "신냉매·냉매전환", "threat_level": "high", "trust_score": 5, "raw_text": "GMCC R290 MBP 신규 진입. 삼성 미보유", "summary": "GMCC R290", "samsung_status": "미보유", "source_name": "GMCC Official", "source_url": "https://example.com/gmcc-r290", "source_type": "official", "source_date": "2026-06-20", "refrigerant": ["R290"], "product_or_series": "R290 MBP", "condition_or_capacity": "MBP", "dynamic_tags": ["R290", "variable"]},
        {"compressor_type": "Ro", "competitor": "LG", "category": "성능·효율", "threat_level": "medium", "trust_score": 5, "raw_text": "LG Ro R32 효율 개선. 삼성 대응 중", "summary": "LG R32", "samsung_status": "대응중", "source_name": "LG Compressor Official", "source_url": "https://www.lg.com/global/business/compressor", "source_type": "official", "source_date": "2026-06-21", "refrigerant": ["R32"], "product_or_series": "R32 Rotary", "condition_or_capacity": "default", "dynamic_tags": ["R32", "performance"]},
        {"compressor_type": "Sc", "competitor": "Copeland/Emerson", "category": "신제품·라인업", "threat_level": "high", "trust_score": 5, "raw_text": "Copeland R454B Variable Scroll 신규. 삼성 미보유", "summary": "Copeland R454B", "samsung_status": "미보유", "source_name": "Copeland Official", "source_url": "https://www.copeland.com", "source_type": "official", "source_date": "2026-06-22", "refrigerant": ["R454B"], "product_or_series": "R454B Variable", "condition_or_capacity": "Variable", "dynamic_tags": ["R454B", "variable"]},
        {"compressor_type": "Sc", "competitor": "Danfoss", "category": "규격·인증", "threat_level": "low", "trust_score": 3, "raw_text": "Danfoss 인증 동향 참고만", "summary": "Danfoss cert", "samsung_status": "보유", "source_name": "Cooling Post", "source_url": "https://www.coolingpost.com", "source_type": "trade_media", "source_date": "2026-06-23", "refrigerant": ["R454B"], "product_or_series": "cert", "condition_or_capacity": "Fixed", "dynamic_tags": ["certification"]},
        {"compressor_type": "Re", "competitor": "Secop", "category": "가격·유통", "threat_level": "none", "trust_score": 3, "raw_text": "수동 입력 stub", "summary": "manual stub", "samsung_status": "확인필요", "source_name": "수동 입력", "source_url": "manual://sample", "source_type": "trade_media", "source_date": "확인필요", "refrigerant": ["R600a"], "product_or_series": "manual", "condition_or_capacity": "LBP", "dynamic_tags": []},
    ]
    return {
        "period_id": "2026-06",
        "score": 10,
        "hard_fail": False,
        "guardian_result": {"severity": "pass"},
        "report_meta": {"total_evidence_count": len(evidence), "high_threat_count": 2, "signal_count": 2},
        "analysis_bundle": {
            "gap_matrix": {
                "Re": {"R290": {"MBP": {"samsung": "미보유", "samsung_status": "미보유", "threat_level": "high", "competitors": [{"name": "GMCC/Midea", "trust_score": 5, "source": "https://www.gmcc.com"}]}}},
                "Ro": {"R32": {"samsung": "대응중", "samsung_status": "대응중", "threat_level": "medium", "competitors": [{"name": "LG", "trust_score": 5, "source": "https://www.lg.com/global/business/compressor"}]}},
                "Sc": {"R454B": {"Variable": {"samsung": "미보유", "samsung_status": "미보유", "threat_level": "high", "competitors": [{"name": "Copeland/Emerson", "trust_score": 5, "source": "https://www.copeland.com"}]}}},
            },
            "threat_summary": [{"compressor_type": "Re", "condition": "MBP", "refrigerant": "R290", "competitor": "GMCC/Midea", "threat_level": "high", "trust_score": 5}],
            "new_signals": [{"signal_type": "primary_new_entry"}, {"signal_type": "new_refrigerant"}],
        },
        "evidence": evidence,
        "sources": [{"source_name": e["source_name"], "source_url": e["source_url"], "source_type": e["source_type"], "source_date": e["source_date"]} for e in evidence],
        "feedback": {"low_confidence": True, "rubric_breakdown": {"structure": 2, "samsung_comparison": 3, "gap_matrix": 2, "evidence_volume": 0.5, "primary_type_coverage": 1, "source_trust": 1, "period_context": "backfill", "evidence_threshold_used": 4, "total": 9.5}},
        "auto_approve_result": {"audit_log": {"approve": True}},
    }


def test_report_html_kpi_decision_layers_and_self_contained():
    draft = "# 압축기 경쟁사 월간 모니터링 리포트\n기간: 2026-06\n\n## 이번 달 핵심 동향 요약\n- high threat\n\n## 다음 달 모니터링 포인트\n- 공식 출처 재검증\n"
    html = markdown_to_html(draft, _sample_state())
    assert "#FF5A5F" in html
    assert "max-width:1200px" in html
    assert html.count('class="kpi-card') >= 6
    assert "삼성 관점 핵심 인사이트" in html
    assert "Decision Matrix" in html
    assert "즉시 라인업 검토" in html
    assert "gap-heatmap heatmap" in html
    assert "Layer 1 Executive Dashboard" in html
    assert "Layer 2 비교 분석" in html
    assert "Layer 3 카테고리 인사이트" in html
    assert "Layer 4 심화 보고서" in html
    assert "<script src=" not in html
    assert "<link rel=" not in html
    assert "📦 과거 데이터" in html
    assert "Critic Review Summary" in html
    assert "rubric-row" in html and "rubric-fill" in html


def test_report_html_stub_url_placeholder_and_real_links():
    html = markdown_to_html("# 압축기 경쟁사 월간 모니터링 리포트", _sample_state())
    assert "stub 데이터 — 실제 출처 없음" in html
    assert 'href="https://example.com' not in html
    assert "manual://sample" not in html
    assert 'href="https://www.lg.com/global/business/compressor" target="_blank" rel="noopener"' in html
    assert 'href="https://www.copeland.com" target="_blank" rel="noopener"' in html


def test_report_html_category_layer_8_tabs_sources_and_insights():
    html = markdown_to_html("# 압축기 경쟁사 월간 모니터링 리포트", _sample_state())
    for category in CATEGORIES:
        assert category in html
        assert f"{category} — 삼성이 알아야 할 것" in html
    assert html.count('data-group="category-tabs"') >= 8
    assert "출처 목록" in html
    assert "저신뢰 — 단정 금지" in html
    assert "https://www.copeland.com" in html


def test_report_html_deepdive_reference_sources_and_trends():
    html = markdown_to_html("# 압축기 경쟁사 월간 모니터링 리포트", _sample_state())
    assert "경쟁사별 심화 보고서" in html
    assert "GMCC/Midea 심화 보고서" in html
    assert "Copeland/Emerson 심화 보고서" in html
    assert "트렌드 인사이트" in html
    assert "삼성 포지셔닝 맵" in html
    assert "월간 변화 요약" in html
    for source in flatten_source_whitelist():
        assert source["name"] in html
        assert source["url"] in html


def test_backfill_html_summary_contains_latest_and_timeline():
    summary = {
        "from_period": "2025-07",
        "to_period": "2026-06",
        "dry_run": True,
        "period_snapshots": [{"period_id": "2025-07", "evidence_count": 4, "evidence_quality": "data_insufficient", "signal_count": 1, "threat_count": 2, "source_boosts": ["Chillventa"]}],
        "latest": {"period_id": "2026-06", "gap_matrix": {"Re": {"R290": {"MBP": {"samsung": "미보유", "threat_level": "high", "period_evidence_quality": "data_insufficient", "competitors": [{"name": "GMCC/Midea"}]}}}}},
        "state_changes": [],
    }
    html = build_backfill_html(summary)
    assert "Backfill Gap Summary" in html
    assert "Period Timeline" in html
    assert "Latest Gap Matrix" in html
    assert "data_insufficient" in html


def test_step6_outputs_html_and_outbox_html():
    state = run_step6("2026-06", dry_run=True)
    paths = state["output_paths"]
    assert Path(paths["report_html"]).exists()
    assert Path(paths["outbox_report_html"]).exists()
    html = Path(paths["report_html"]).read_text(encoding="utf-8")
    assert "#FF5A5F" in html
    assert "삼성 관점 핵심 인사이트" in html
    assert "gap-heatmap heatmap" in html


def test_gmail_payload_includes_html_attachment_and_body():
    state = run_step6("2026-06", dry_run=True)
    payload_path = Path(state["output_paths"]["email_payload"])
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert any(item.endswith(".md") for item in payload["attachments"])
    assert any(item.endswith(".html") for item in payload["attachments"])
    assert "html_body" in payload and "#FF5A5F" in payload["html_body"]
    assert "삼성 관점 핵심 인사이트" in payload["html_body"]
    live_payloads = build_live_payloads(state)
    assert any(item.endswith(".html") for item in live_payloads["email"]["attachments"])
    assert "HTML:" in live_payloads["slack"]["message"]
