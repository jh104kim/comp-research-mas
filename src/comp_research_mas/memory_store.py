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


def normalize_period_id(period_id: str | None = None, week_id: str | None = None) -> str:
    value = period_id or week_id or "unknown"
    # YYYY-WW legacy -> keep as-is for legacy runs. YYYY-MM monthly is preferred.
    return value


def append_evidence_ledger(week_id: str, evidence: list[dict[str, Any]], reasoning_log: list[dict[str, Any]] | None = None, period_id: str | None = None) -> Path:
    period = normalize_period_id(period_id, week_id)
    ledger = _read_json(EVIDENCE_LEDGER_PATH, {"periods": {}, "weeks": {}})
    ledger.setdefault("periods", {})[period] = {"period_id": period, "week_id": week_id, "evidence": evidence, "reasoning_log": reasoning_log or []}
    # Backward compatibility for old tests/consumers.
    ledger.setdefault("weeks", {})[week_id] = {"evidence": evidence, "reasoning_log": reasoning_log or []}
    _write_json(EVIDENCE_LEDGER_PATH, ledger)
    return EVIDENCE_LEDGER_PATH


def read_evidence_ledger() -> dict[str, Any]:
    return _read_json(EVIDENCE_LEDGER_PATH, {"periods": {}, "weeks": {}})


def append_gap_history(week_id: str, analysis_bundle: dict[str, Any], reasoning_log: list[dict[str, Any]] | None = None, period_id: str | None = None) -> Path:
    period = normalize_period_id(period_id, week_id)
    history = _read_json(GAP_HISTORY_PATH, {"periods": {}, "weeks": {}})
    payload = {"period_id": period, "week_id": week_id, "gap_matrix": analysis_bundle.get("gap_matrix", {}), "new_signals": analysis_bundle.get("new_signals", []), "reasoning_log": reasoning_log or []}
    history.setdefault("periods", {})[period] = payload
    history.setdefault("weeks", {})[week_id] = {"gap_matrix": payload["gap_matrix"], "new_signals": payload["new_signals"], "reasoning_log": payload["reasoning_log"]}
    _write_json(GAP_HISTORY_PATH, history)
    return GAP_HISTORY_PATH


def read_gap_history() -> dict[str, Any]:
    return _read_json(GAP_HISTORY_PATH, {"periods": {}, "weeks": {}})


def previous_period_id(current_period_id: str) -> str | None:
    try:
        year_s, month_s = current_period_id.split("-")
        year, month = int(year_s), int(month_s)
        if month == 1:
            return f"{year - 1}-12"
        return f"{year}-{month - 1:02d}"
    except Exception:
        return None


def previous_week_id(current_week_id: str) -> str | None:
    try:
        year, week = current_week_id.split("-")
        week_num = int(week)
        if week_num <= 1:
            return None
        return f"{year}-{week_num - 1:02d}"
    except Exception:
        return None


def previous_gap_matrix(current_week_id: str, period_id: str | None = None) -> dict[str, Any] | None:
    history = read_gap_history()
    if period_id:
        prev_period = previous_period_id(period_id)
        if prev_period:
            matrix = history.get("periods", {}).get(prev_period, {}).get("gap_matrix")
            if matrix:
                return matrix
    prev = previous_week_id(current_week_id)
    if not prev:
        return None
    return history.get("weeks", {}).get(prev, {}).get("gap_matrix")


def get_previous_period_evidence(competitor: str, category: str, period_id: str | None = None) -> list[dict[str, Any]]:
    ledger = read_evidence_ledger()
    periods = ledger.get("periods", {})
    target_period = previous_period_id(period_id) if period_id else None
    if not target_period and periods:
        target_period = sorted(periods)[-1]
    evidence = periods.get(target_period or "", {}).get("evidence", [])
    return [item for item in evidence if item.get("competitor") == competitor and item.get("category") == category]


def get_gap_status_change(compressor_type: str, refrigerant: str, condition: str, period_id: str | None = None) -> dict[str, Any] | None:
    history = read_gap_history()
    current = history.get("periods", {}).get(period_id or "", {}).get("gap_matrix")
    prev_period = previous_period_id(period_id or "")
    previous = history.get("periods", {}).get(prev_period or "", {}).get("gap_matrix")
    if not current or not previous:
        return None
    def status(matrix: dict[str, Any]) -> str | None:
        node = matrix.get(compressor_type, {}).get(refrigerant)
        if not isinstance(node, dict):
            return None
        if "samsung_status" in node or "samsung" in node:
            return node.get("samsung_status") or node.get("samsung")
        cell = node.get(condition)
        if isinstance(cell, dict):
            return cell.get("samsung_status") or cell.get("samsung")
        return None
    before, after = status(previous), status(current)
    if before and after and before != after:
        return {"from": before, "to": after, "period_id": period_id, "previous_period_id": prev_period}
    return None


def previous_report_text() -> str:
    reports = sorted(Path("outputs/reports").glob("*_compressor_weekly.md"))
    if len(reports) < 2:
        return ""
    return reports[-2].read_text(encoding="utf-8")
