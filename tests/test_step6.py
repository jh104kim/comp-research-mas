import json
from pathlib import Path

from comp_research_mas.auto_approver import evaluate_auto_approve, write_auto_approve_log
from comp_research_mas.graph import run_step6
from comp_research_mas.hermes_adapter import HermesLiveAdapter
from comp_research_mas.live_sender import build_live_payloads, live_sender_node
from comp_research_mas.query_planner import build_query_plan


def _state(score=10, hard_fail=False, guardian="pass"):
    return {
        "period_id": "2026-06",
        "score": score,
        "hard_fail": hard_fail,
        "guardian_result": {"severity": guardian},
        "draft": "# report\n\n## 이번 주 핵심 동향 요약\n- 핵심\n",
        "analysis_bundle": {"threat_summary": [{"threat_level": "high"}], "new_signals": [{}]},
        "output_paths": {"report": "outputs/reports/2026-06_compressor_monthly.md"},
        "reasoning_log": [],
    }


def test_auto_approver_approve_and_blocks():
    ok = evaluate_auto_approve(_state(score=9, hard_fail=False, guardian="pass"))
    assert ok.approve is True
    assert ok.audit_log["conditions"]["critic_score>=9"] is True
    assert evaluate_auto_approve(_state(score=8)).approve is False
    assert evaluate_auto_approve(_state(hard_fail=True)).approve is False
    assert evaluate_auto_approve(_state(guardian="block")).approve is False


def test_auto_approver_audit_log(tmp_path, monkeypatch):
    monkeypatch.chdir(Path.cwd())
    result = evaluate_auto_approve(_state())
    path = write_auto_approve_log(result, "2026-06")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["approve"] is True


def test_live_sender_payloads_and_dry_run_outputs():
    report = Path("outputs/reports/2026-06_compressor_monthly.md")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("# report\n\n## 이번 주 핵심 동향 요약\n- 핵심\n", encoding="utf-8")
    state = _state()
    payloads = build_live_payloads(state)
    assert payloads["email"]["to"] == "jh104.kim@samsung.com"
    assert payloads["email"]["attachment"].endswith(".md")
    assert "자동 승인" in payloads["slack"]["message"]
    assert payloads["obsidian"]["filename"] == "2026-06_compressor_monthly.md"

    result = live_sender_node({**state, "dry_run": True})
    assert Path(result["output_paths"]["live_sender"]).exists()
    assert result["live_send_results"]["gmail"]["dry_run"] is True
    assert Path(result["output_paths"]["email_payload"]).exists()


def test_hermes_live_adapter_decision_and_fallback():
    plan = build_query_plan("2026-26", period_id="2026-06")
    adapter = HermesLiveAdapter()
    raw = adapter.search(plan)
    assert raw["results"]
    assert adapter.last_decision["mode"] == "stub_fallback"


def test_hermes_live_adapter_injected_choice(tmp_path):
    plan = build_query_plan("2026-26", period_id="2026-06")
    raw = {
        "period_id": "2026-06",
        "week_id": "2026-26",
        "results": [
            {
                "query_id": "q1",
                "source_url": "https://example.com/a",
                "source_date": "2026-06-01",
                "source_type": "official",
                "title": "title",
                "summary": "summary",
                "raw_text": "raw",
                "competitor": "GMCC/Midea",
                "compressor_type": "Re",
                "category": "신제품·라인업",
                "refrigerants": ["R290"],
                "samsung_status": "미보유",
            }
        ],
    }
    path = tmp_path / "raw.json"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    adapter = HermesLiveAdapter(str(path))
    loaded = adapter.search(plan)
    assert loaded["results"][0]["query_id"] == "q1"
    assert adapter.last_decision["mode"] == "injected_json"


def test_step6_graph_e2e_dry_run():
    state = run_step6("2026-06", dry_run=True)
    assert state["status"] == "saved"
    assert state["auto_approve"] is True
    assert state["live_send_results"]["gmail"]["dry_run"] is True
    assert state["hermes_live_decision"]["mode"] in {"stub_fallback", "injected_json"}
    paths = state["output_paths"]
    assert Path(paths["auto_approve"]).exists()
    assert Path(paths["live_sender"]).exists()
    assert Path(paths["email_payload"]).exists()
