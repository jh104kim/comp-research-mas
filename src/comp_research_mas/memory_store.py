from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MEMORY_DIR = Path("outputs/memory")
EVIDENCE_LEDGER_PATH = MEMORY_DIR / "evidence_ledger.json"
GAP_HISTORY_PATH = MEMORY_DIR / "gap_matrix_history.json"


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_evidence_ledger(week_id: str, evidence: list[dict[str, Any]], reasoning_log: list[dict[str, Any]] | None = None) -> Path:
    ledger = _read_json(EVIDENCE_LEDGER_PATH, {"weeks": {}})
    ledger.setdefault("weeks", {})[week_id] = {"evidence": evidence, "reasoning_log": reasoning_log or []}
    _write_json(EVIDENCE_LEDGER_PATH, ledger)
    return EVIDENCE_LEDGER_PATH


def read_evidence_ledger() -> dict[str, Any]:
    return _read_json(EVIDENCE_LEDGER_PATH, {"weeks": {}})


def append_gap_history(week_id: str, analysis_bundle: dict[str, Any], reasoning_log: list[dict[str, Any]] | None = None) -> Path:
    history = _read_json(GAP_HISTORY_PATH, {"weeks": {}})
    history.setdefault("weeks", {})[week_id] = {"gap_matrix": analysis_bundle.get("gap_matrix", {}), "new_signals": analysis_bundle.get("new_signals", []), "reasoning_log": reasoning_log or []}
    _write_json(GAP_HISTORY_PATH, history)
    return GAP_HISTORY_PATH


def read_gap_history() -> dict[str, Any]:
    return _read_json(GAP_HISTORY_PATH, {"weeks": {}})


def previous_week_id(current_week_id: str) -> str | None:
    try:
        year, week = current_week_id.split("-")
        week_num = int(week)
        if week_num <= 1:
            return None
        return f"{year}-{week_num - 1:02d}"
    except Exception:
        return None


def previous_gap_matrix(current_week_id: str) -> dict[str, Any] | None:
    prev = previous_week_id(current_week_id)
    if not prev:
        return None
    return read_gap_history().get("weeks", {}).get(prev, {}).get("gap_matrix")


def previous_report_text() -> str:
    reports = sorted(Path("outputs/reports").glob("*_compressor_weekly.md"))
    if len(reports) < 2:
        return ""
    return reports[-2].read_text(encoding="utf-8")
