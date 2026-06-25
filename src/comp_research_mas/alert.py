from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


DEFAULT_POLICY = {
    "high": {"action": "slack_immediate", "dry_run": True},
    "medium": {"action": "monthly_report"},
    "low": {"action": "ledger_only"},
}


def load_alert_policy(path: str | Path = "config/alert_policy.yaml") -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return DEFAULT_POLICY
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("alerts", data) or DEFAULT_POLICY


def emit_alert(kind: str, message: str, *, period_id: str = "unknown", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    alert = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "kind": kind,
        "period_id": period_id,
        "message": message,
        "payload": payload or {},
    }
    line = f"[ALERT][{alert['timestamp']}][{kind}] {period_id} {message}\n"
    log_dir = Path("outputs/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{period_id}_alerts.log").open("a", encoding="utf-8").write(line)
    return alert


def detect_high_threat_alerts(evidence: list[dict[str, Any]], *, period_id: str) -> dict[str, Any]:
    policy = load_alert_policy()
    high_items = [item for item in evidence if item.get("threat_level") == "high"]
    alerts = [emit_alert("high_threat", f"high threat detected: {item.get('compressor_type')} {item.get('competitor')} {item.get('refrigerant')}", period_id=period_id, payload=item) for item in high_items]
    slack_payload = {
        "dry_run": bool(policy.get("high", {}).get("dry_run", True)),
        "message": f"[High Threat] {period_id}: {len(high_items)}건 감지",
        "items": [{"competitor": i.get("competitor"), "type": i.get("compressor_type"), "refrigerant": i.get("refrigerant"), "source": i.get("source_url")} for i in high_items[:5]],
    }
    out = Path("outputs/outbox") / period_id / "alert_slack_payload.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(slack_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"count": len(high_items), "alerts": alerts, "slack_payload_path": str(out), "dry_run": slack_payload["dry_run"]}
