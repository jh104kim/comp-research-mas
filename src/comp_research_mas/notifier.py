from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .guardian import scan_state, write_guardian_log

OBSIDIAN_TAGS = ["#compressor", "#monthly", "#competitor", "#Re", "#Ro", "#Sc", "#samsung-gap"]
OBSIDIAN_VAULT_PLACEHOLDER = "[헤르메스가 알고 있는 경로]"
GMAIL_RECIPIENT = "jh104.kim@samsung.com"


def _extract_summary(markdown: str) -> str:
    marker = "## 이번 주 핵심 동향 요약"
    if marker not in markdown:
        return markdown[:1000]
    after = markdown.split(marker, 1)[1]
    end = after.find("\n## ")
    section = after if end == -1 else after[:end]
    return marker + section.strip()


def prepare_notifier_dry_run(state: dict[str, Any], *, approve_send: bool = False) -> dict[str, Any]:
    period_id = state.get("period_id", "unknown")
    guardian = scan_state(state)
    write_guardian_log(guardian, period_id)
    dry_run = not approve_send
    report_path = Path((state.get("output_paths") or {}).get("report", f"outputs/reports/{period_id}_compressor_monthly.md"))
    report_text = state.get("draft") or (report_path.read_text(encoding="utf-8") if report_path.exists() else "")
    outbox = Path("outputs/outbox") / period_id
    outbox.mkdir(parents=True, exist_ok=True)
    report_copy = outbox / "report.md"
    report_copy.write_text(report_text, encoding="utf-8")

    meta = state.get("report_meta") or {}
    if not meta and isinstance(state.get("analysis_bundle"), dict):
        bundle = state["analysis_bundle"]
        meta = {
            "high_threat_count": sum(1 for item in bundle.get("threat_summary", []) if item.get("threat_level") == "high"),
            "signal_count": len(bundle.get("new_signals", [])),
        }
    email_payload = {
        "dry_run": dry_run,
        "to": GMAIL_RECIPIENT,
        "subject": f"[월간] 압축기 경쟁사 모니터링 {period_id}",
        "body": _extract_summary(report_text),
        "attachment": str(report_path),
        "attachment_note": "Obsidian 인제스트용 md 파일 첨부",
    }
    slack_payload = {
        "dry_run": dry_run,
        "message": f"[월간] 압축기 리포트 생성 완료 {period_id}\nhigh_threat: {meta.get('high_threat_count', 0)}건 / signal: {meta.get('signal_count', 0)}건\n파일: {report_path}",
        "human_review": bool(state.get("human_review_flag") or state.get("auto_publish_blocked")),
        "hard_fail": bool(state.get("hard_fail")),
        "reasons": state.get("error_log", []),
    }
    obsidian_payload = {
        "dry_run": dry_run,
        "vault_path": OBSIDIAN_VAULT_PLACEHOLDER,
        "filename": f"{period_id}_compressor_monthly.md",
        "tags": OBSIDIAN_TAGS,
        "content": report_text,
    }
    for name, payload in [("email_payload.json", email_payload), ("slack_payload.json", slack_payload), ("obsidian_payload.json", obsidian_payload)]:
        (outbox / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log_path = Path("outputs/logs") / f"{period_id}_notifier_dry_run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(f"dry_run={dry_run}\napprove_send={approve_send}\noutbox={outbox}\nguardian={guardian.severity}\n", encoding="utf-8")
    return {
        **state,
        "notifier_dry_run": dry_run,
        "notifier_outbox": str(outbox),
        "notifier_log_path": str(log_path),
        "email_payload_path": str(outbox / "email_payload.json"),
        "slack_payload_path": str(outbox / "slack_payload.json"),
        "obsidian_payload_path": str(outbox / "obsidian_payload.json"),
        "output_paths": {**state.get("output_paths", {}), "notifier_dry_run": str(log_path), "outbox_report": str(report_copy), "email_payload": str(outbox / "email_payload.json"), "slack_payload": str(outbox / "slack_payload.json"), "obsidian_payload": str(outbox / "obsidian_payload.json")},
    }


def notifier_node(state: dict[str, Any]) -> dict[str, Any]:
    approve_send = bool(state.get("approve_send", False))
    # STEP 5: even run-step5-live stays dry-run unless explicit approval is passed.
    return prepare_notifier_dry_run(state, approve_send=approve_send)
