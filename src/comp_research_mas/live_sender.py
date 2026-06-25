from __future__ import annotations

import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from urllib import request

from .notifier import GMAIL_RECIPIENT, OBSIDIAN_TAGS, _extract_summary, prepare_notifier_dry_run

DEFAULT_GMAIL_SENDER = "jh104.kim@gmail.com"


class LiveSendError(RuntimeError):
    pass


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _report_path(state: dict[str, Any]) -> Path:
    period_id = state.get("period_id", "unknown")
    return Path((state.get("output_paths") or {}).get("report", f"outputs/reports/{period_id}_compressor_monthly.md"))


def build_live_payloads(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    period_id = state.get("period_id", "unknown")
    report_path = _report_path(state)
    report_text = state.get("draft") or (report_path.read_text(encoding="utf-8") if report_path.exists() else "")
    meta = state.get("report_meta") or {}
    if not meta and isinstance(state.get("analysis_bundle"), dict):
        bundle = state["analysis_bundle"]
        meta = {"high_threat_count": sum(1 for item in bundle.get("threat_summary", []) if item.get("threat_level") == "high"), "signal_count": len(bundle.get("new_signals", []))}
    score = int(state.get("score", 0))
    guardian = (state.get("guardian_result") or {}).get("severity", "pass")
    email_payload = {
        "from": os.environ.get("GMAIL_SENDER", DEFAULT_GMAIL_SENDER),
        "to": GMAIL_RECIPIENT,
        "subject": f"[월간] 압축기 경쟁사 모니터링 {period_id}",
        "body": _extract_summary(report_text),
        "attachment": str(report_path),
    }
    slack_payload = {
        "message": f"[자동 승인] 월간 리포트 발송 완료 {period_id}\ncritic_score: {score} / high_threat: {meta.get('high_threat_count', 0)}건 / signal: {meta.get('signal_count', 0)}건\n파일: {report_path}\n자동 승인 조건 충족: score={score}, hard_fail=False, guardian={guardian}",
    }
    obsidian_payload = {
        "vault_path": os.environ.get("OBSIDIAN_VAULT_PATH", "/mnt/f/ai-obsidian/지식창고"),
        "filename": f"{period_id}_compressor_monthly.md",
        "tags": OBSIDIAN_TAGS,
        "content": report_text,
    }
    return {"email": email_payload, "slack": slack_payload, "obsidian": obsidian_payload}


def send_gmail(payload: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"sent": False, "dry_run": True, "channel": "gmail"}
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        raise LiveSendError("GMAIL_APP_PASSWORD missing")
    attachment = Path(payload["attachment"])
    if not attachment.exists() or attachment.suffix != ".md":
        raise LiveSendError("Gmail attachment .md missing")
    msg = EmailMessage()
    msg["From"] = payload["from"]
    msg["To"] = payload["to"]
    msg["Subject"] = payload["subject"]
    msg.set_content(payload["body"])
    msg.add_attachment(attachment.read_bytes(), maintype="text", subtype="markdown", filename=attachment.name)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(payload["from"], password)
        smtp.send_message(msg)
    return {"sent": True, "dry_run": False, "channel": "gmail"}


def send_slack(payload: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"sent": False, "dry_run": True, "channel": "slack"}
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        raise LiveSendError("SLACK_WEBHOOK_URL missing")
    req = request.Request(webhook, data=json.dumps({"text": payload["message"]}).encode("utf-8"), headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=20) as resp:  # nosec - URL is user-provided env var
        status = resp.status
    if status >= 300:
        raise LiveSendError(f"Slack webhook failed status={status}")
    return {"sent": True, "dry_run": False, "channel": "slack", "status": status}


def save_obsidian(payload: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    vault = Path(payload["vault_path"])
    target = vault / payload["filename"]
    if dry_run:
        return {"sent": False, "dry_run": True, "channel": "obsidian", "target": str(target)}
    vault.mkdir(parents=True, exist_ok=True)
    content = " ".join(payload["tags"]) + "\n\n" + payload["content"]
    target.write_text(content, encoding="utf-8")
    return {"sent": True, "dry_run": False, "channel": "obsidian", "target": str(target)}


def live_sender_node(state: dict[str, Any]) -> dict[str, Any]:
    period_id = state.get("period_id", "unknown")
    dry_run = bool(state.get("dry_run", True))
    # Always keep STEP5-style outbox payloads for audit, even in live mode.
    state = prepare_notifier_dry_run(state, approve_send=not dry_run)
    payloads = build_live_payloads(state)
    outbox = Path("outputs/outbox") / period_id
    _write_json(outbox / "email_payload.json", {"dry_run": dry_run, **payloads["email"]})
    _write_json(outbox / "slack_payload.json", {"dry_run": dry_run, **payloads["slack"]})
    _write_json(outbox / "obsidian_payload.json", {"dry_run": dry_run, **payloads["obsidian"]})
    results = {
        "gmail": send_gmail(payloads["email"], dry_run=dry_run),
        "obsidian": save_obsidian(payloads["obsidian"], dry_run=dry_run),
        "slack": send_slack(payloads["slack"], dry_run=dry_run),
    }
    log_path = Path("outputs/logs") / f"{period_id}_live_sender.log"
    _write_json(log_path, {"dry_run": dry_run, "results": results})
    from .workflow_utils import append_reasoning
    reasoning_log = append_reasoning(
        state,
        node="live_sender",
        step="Gmail/Slack/Obsidian 발송",
        judgment="dry_run" if dry_run else "sent",
        reasoning="자동 승인 후 발송 payload를 생성하고 dry_run 또는 live 전송 수행",
        tool_used=True,
        rag_used=False,
        conclusion=str(results),
    )
    return {**state, "live_send_results": results, "live_sender_log_path": str(log_path), "reasoning_log": reasoning_log, "output_paths": {**state.get("output_paths", {}), "live_sender": str(log_path)}}
