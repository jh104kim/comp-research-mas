from __future__ import annotations

import copy
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from .memory_store import previous_gap_matrix
from .models import AnalysisBundle, EvidenceItem, PRIMARY_COMPETITORS, SignalItem, ThreatItem

BASELINE_PATH = Path("config/gap_matrix_baseline.yaml")


def load_gap_baseline(path: str | Path = BASELINE_PATH) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def analyst_threat_level(samsung_status: str, trust_score: int) -> str:
    if samsung_status == "미보유" and trust_score == 5:
        return "high"
    if samsung_status == "미보유" and trust_score in {3, 4}:
        return "medium"
    if samsung_status == "대응중" and trust_score >= 4:
        return "medium"
    if samsung_status == "대응중" and trust_score == 3:
        return "low"
    if samsung_status == "보유":
        return "low"
    return "none"


def signal_allowed(signal_type: str, trust_score: int) -> bool:
    if signal_type == "primary_new_entry":
        return trust_score >= 4
    return trust_score == 5


def infer_condition(item: EvidenceItem, baseline: dict[str, Any]) -> str:
    text = " ".join([item.condition_or_capacity, item.product_or_series, item.raw_text, " ".join(item.dynamic_tags)])
    if item.compressor_type == "Re":
        for condition in ("MBP", "LBP", "HBP"):
            if condition in text:
                return condition
        for ref in item.refrigerant:
            node = baseline.get("Re", {}).get(ref)
            if isinstance(node, dict):
                return next(iter(node.keys()))
        return "MBP"
    if item.compressor_type == "Sc":
        if any(token in text for token in ("Variable", "variable", "인버터")):
            return "Variable"
        if any(token in text for token in ("TwoStage", "Two-Stage", "two-stage", "2-stage")):
            return "TwoStage"
        if any(token in text for token in ("Fixed", "fixed")):
            return "Fixed"
        return "Fixed"
    return "default"


def baseline_status(matrix: dict[str, Any], ctype: str, refrigerant: str, condition: str) -> str:
    node = matrix.setdefault(ctype, {}).setdefault(refrigerant, {})
    if ctype in {"Re", "Sc"}:
        if not isinstance(node, dict) or "samsung" in node:
            matrix[ctype][refrigerant] = {condition: {"samsung": node.get("samsung", "확인필요") if isinstance(node, dict) else "확인필요", "note": "evidence 기반 추론"}}
        return matrix[ctype][refrigerant].setdefault(condition, {"samsung": "확인필요", "note": "evidence 기반 추론"}).get("samsung", "확인필요")
    if isinstance(node, dict) and "samsung" in node:
        return node["samsung"]
    matrix[ctype][refrigerant] = {"samsung": "확인필요", "note": "evidence 기반 추론"}
    return "확인필요"


def _previous_cell_status(prev_matrix: dict[str, Any] | None, ctype: str, ref: str, condition: str) -> str | None:
    if not prev_matrix:
        return None
    node = prev_matrix.get(ctype, {}).get(ref)
    if not isinstance(node, dict):
        return None
    if "samsung_status" in node or "samsung" in node:
        return node.get("samsung_status") or node.get("samsung")
    cell = node.get(condition)
    if isinstance(cell, dict):
        return cell.get("samsung_status") or cell.get("samsung")
    return None


def build_analysis_bundle(evidence: list[EvidenceItem], week_id: str, baseline_path: str | Path = BASELINE_PATH) -> AnalysisBundle:
    baseline = load_gap_baseline(baseline_path)
    prev_matrix = previous_gap_matrix(week_id)
    matrix = copy.deepcopy(baseline)
    threats: list[ThreatItem] = []
    signals: list[SignalItem] = []
    entries_by_gap: dict[tuple[str, str, str], list[EvidenceItem]] = defaultdict(list)

    for item in evidence:
        if item.trust_score < 3:
            continue
        for ref in item.refrigerant:
            if ref == "확인필요":
                continue
            condition = infer_condition(item, matrix)
            samsung = baseline_status(matrix, item.compressor_type, ref, condition)
            level = analyst_threat_level(samsung, item.trust_score)
            entry = {"name": item.competitor, "model": item.product_or_series, "trust_score": item.trust_score, "source": item.source_url, "evidence_id": item.to_dict()["evidence_id"]}
            if item.compressor_type in {"Re", "Sc"}:
                cell = matrix[item.compressor_type][ref].setdefault(condition, {"samsung": samsung, "note": "evidence 기반 추론"})
            else:
                cell = matrix[item.compressor_type].setdefault(ref, {"samsung": samsung, "note": "evidence 기반 추론"})
            cell["samsung_status"] = samsung
            cell["threat_level"] = level
            cell.setdefault("competitors", [])
            if not any(c.get("name") == item.competitor and c.get("source") == item.source_url for c in cell["competitors"]):
                cell["competitors"].append(entry)
            entries_by_gap[(item.compressor_type, ref, condition)].append(item)
            if level in {"high", "medium", "low"}:
                threats.append(ThreatItem(item.compressor_type, ref, condition, item.competitor, level, item.trust_score, [item.to_dict()["evidence_id"]]))
            if samsung == "미보유" and item.competitor in PRIMARY_COMPETITORS.get(item.compressor_type, []) and signal_allowed("primary_new_entry", item.trust_score):
                signals.append(SignalItem("primary_new_entry", f"★ 최우선 {item.competitor}가 {item.compressor_type}/{ref}/{condition} 삼성 미보유 구간에 진입", item.competitor, item.trust_score, week_id))
            if samsung == "미보유" and signal_allowed("new_refrigerant", item.trust_score):
                signals.append(SignalItem("new_refrigerant", f"삼성 미보유 냉매 {ref} 구간에서 {item.competitor} 근거 감지", item.competitor, item.trust_score, week_id))
            if ("재등장" in item.raw_text or "2주" in item.raw_text or "spec_change" in item.dynamic_tags) and signal_allowed("spec_change", item.trust_score):
                signals.append(SignalItem("spec_change", f"동일 모델 단기 재등장/스펙 급변 후보: {item.product_or_series}", item.competitor, item.trust_score, week_id))
            prev_status = _previous_cell_status(prev_matrix, item.compressor_type, ref, condition)
            if prev_status and prev_status != samsung and signal_allowed("spec_change", item.trust_score):
                signals.append(SignalItem("spec_change", f"전주 대비 Gap 상태 변경: {item.compressor_type}/{ref}/{condition} {prev_status}→{samsung}", item.competitor, item.trust_score, week_id))

    for (ctype, ref, condition), items in entries_by_gap.items():
        competitors = sorted({item.competitor for item in items})
        samsung = baseline_status(matrix, ctype, ref, condition)
        max_score = max(item.trust_score for item in items)
        if samsung == "미보유" and len(competitors) >= 2 and signal_allowed("multi_competitor_entry", max_score):
            signals.append(SignalItem("multi_competitor_entry", f"{ctype}/{ref}/{condition} 삼성 미보유 구간에 복수 경쟁사 동시 진입: {', '.join(competitors)}", ", ".join(competitors), max_score, week_id))

    seen = set()
    unique_signals = []
    for signal in signals:
        key = (signal.signal_type, signal.description)
        if key not in seen:
            seen.add(key)
            unique_signals.append(signal)

    threats = sorted(threats, key=lambda t: ({"high": 0, "medium": 1, "low": 2}[t.threat_level], -t.trust_score))
    return AnalysisBundle(matrix, threats, unique_signals, week_id, Path(baseline_path).name)


def save_analysis_bundle(bundle: AnalysisBundle, output_dir: str | Path = "outputs/analysis") -> Path:
    path = Path(output_dir) / f"{bundle.week_id}_analysis_bundle.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def orchestrator_directives(bundle: AnalysisBundle | None) -> list[str]:
    if bundle is None:
        return ["AnalysisBundle empty: evidence 기반 fallback 사용"]
    directives = []
    if any(item.threat_level == "high" for item in bundle.threat_summary):
        directives.append("high threat 항목을 핵심 동향 최상단에 배치")
    if bundle.new_signals:
        directives.append("new_signals를 핵심 동향 별도 섹션에 배치")
    if not bundle.threat_summary and not bundle.new_signals:
        directives.append("AnalysisBundle empty: evidence 기반 fallback 사용")
    return directives
