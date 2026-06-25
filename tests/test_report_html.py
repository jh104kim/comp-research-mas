import json
from pathlib import Path

from comp_research_mas.graph import run_step6
from comp_research_mas.live_sender import build_live_payloads
from comp_research_mas.report_html import markdown_to_html


def test_report_html_airbnb_style_contains_required_tokens():
    state = {
        "period_id": "2026-06",
        "score": 10,
        "hard_fail": False,
        "guardian_result": {"severity": "pass"},
        "report_meta": {"total_evidence_count": 1, "high_threat_count": 1, "signal_count": 1},
        "analysis_bundle": {"threat_summary": [{"compressor_type": "Re", "condition": "MBP", "refrigerant": "R290", "competitor": "GMCC/Midea", "threat_level": "high", "trust_score": 5}], "new_signals": [{}]},
        "evidence": [{"compressor_type": "Re", "competitor": "GMCC/Midea", "category": "신제품·라인업", "threat_level": "high", "trust_score": 5, "raw_text": "high threat", "samsung_status": "미보유", "source_name": "official", "source_date": "2026-06-20", "refrigerant": ["R290"]}],
        "sources": [],
        "auto_approve_result": {"audit_log": {"approve": True}},
    }
    draft = "# 압축기 경쟁사 월간 모니터링 리포트\n기간: 2026-06\n\n## 이번 달 핵심 동향 요약\n- high threat\n\n## 다음 달 모니터링 포인트\n- 공식 출처 재검증\n"
    html = markdown_to_html(draft, state)
    assert "#FF5A5F" in html
    assert "max-width:960px" in html
    assert "border-radius:12px" in html
    assert "threat-high" in html
    assert "2026-06" in html


def test_step6_outputs_html_and_outbox_html():
    state = run_step6("2026-06", dry_run=True)
    paths = state["output_paths"]
    assert Path(paths["report_html"]).exists()
    assert Path(paths["outbox_report_html"]).exists()
    html = Path(paths["report_html"]).read_text(encoding="utf-8")
    assert "#FF5A5F" in html
    assert "threat-high" in html


def test_gmail_payload_includes_html_attachment_and_body():
    state = run_step6("2026-06", dry_run=True)
    payload_path = Path(state["output_paths"]["email_payload"])
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert any(item.endswith(".md") for item in payload["attachments"])
    assert any(item.endswith(".html") for item in payload["attachments"])
    assert "html_body" in payload and "#FF5A5F" in payload["html_body"]
    live_payloads = build_live_payloads(state)
    assert any(item.endswith(".html") for item in live_payloads["email"]["attachments"])
    assert "HTML:" in live_payloads["slack"]["message"]
