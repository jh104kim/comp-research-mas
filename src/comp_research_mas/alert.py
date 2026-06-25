from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


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
    print(line.rstrip())
    return alert
