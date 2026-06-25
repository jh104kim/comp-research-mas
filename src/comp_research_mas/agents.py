from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import MAX_ITERATIONS, PASS_SCORE, REPORT_TITLE
from .models import CATEGORIES, NO_EVIDENCE_TEXT, PRIMARY_COMPETITORS, TYPE_LABELS, AnalysisBundle, EvidenceItem, ReportMetadata, SignalItem, ThreatItem, WorkflowState
from .tools import evidence_to_dicts, parse_step1_raw_data

DISPLAY_STATUS = {"보유": "보유", "미보유": "미보유", "대응중": "대응 중", "확인필요": "확인 필요"}


def load_raw_data_node(state: WorkflowState) -> WorkflowState:
    raw_data = state.get("raw_data", "")
    week_id = state.get("week_id", "2026-26")
    evidence = parse_step1_raw_data(raw_data, week_id=week_id)
    return {**state, "week_id": week_id, "evidence": evidence_to_dicts(evidence), "sources": _sources(evidence), "gap_table": _gap_rows(evidence), "iteration": int(state.get("iteration", 0)), "error_log": list(state.get("error_log", [])), "status": "loaded"}


def writer_node(state: WorkflowState) -> WorkflowState:
    evidence = [EvidenceItem(**item) for item in state.get("evidence", [])]
    draft = write_step_report(evidence, analysis_bundle=state.get("analysis_bundle"), writer_directives=state.get("writer_directives", []), feedback=state.get("feedback"), iteration=int(state.get("iteration", 0)))
    return {**state, "draft": draft, "status": "drafted"}


def critic_node(state: WorkflowState) -> WorkflowState:
    review = critique_step_report(state.get("draft", ""), state.get("evidence", []), int(state.get("iteration", 0)), analysis_bundle=state.get("analysis_bundle"))
    return {**state, "score": review["score"], "feedback": review, "hard_fail": review["hard_fail"], "error_log": list(state.get("error_log", [])) + review["hard_fail_reasons"], "status": "reviewed"}


def human_review_flag_node(state: WorkflowState) -> WorkflowState:
    return {**state, "status": "human_review_required"}


def decide_after_critic(state: WorkflowState) -> str:
    if state.get("hard_fail"):
        return "human_review"
    if int(state.get("score", 0)) >= PASS_SCORE:
        return "save"
    if int(state.get("iteration", 0)) < MAX_ITERATIONS:
        return "rewrite"
    return "human_review"


def increment_iteration_node(state: WorkflowState) -> WorkflowState:
    return {**state, "iteration": int(state.get("iteration", 0)) + 1, "status": "rewriting"}


def write_step1_report(evidence: list[EvidenceItem], *, feedback: dict[str, Any] | None = None, iteration: int = 0) -> str:
    return write_step_report(evidence, feedback=feedback, iteration=iteration)


def write_step_report(evidence: list[EvidenceItem], *, analysis_bundle: dict[str, Any] | None = None, writer_directives: list[str] | None = None, feedback: dict[str, Any] | None = None, iteration: int = 0) -> str:
    writer_directives = writer_directives or []
    by_type_category_competitor: dict[tuple[str, str, str], list[EvidenceItem]] = defaultdict(list)
    for item in evidence:
        by_type_category_competitor[(item.compressor_type, item.category, item.competitor)].append(item)

    lines: list[str] = []
    lines.append(f"# {REPORT_TITLE}")
    lines.append(f"날짜: {evidence[0].week_id if evidence else (analysis_bundle or {}).get('week_id', 'STEP SAMPLE')}")
    lines.append("")
    lines.append("## 이번 주 핵심 동향 요약")
    if writer_directives:
        lines.append("- Orchestrator 지시: " + " / ".join(writer_directives))
    if analysis_bundle:
        threats = analysis_bundle.get("threat_summary", [])
        high = [t for t in threats if t.get("threat_level") == "high"]
        focus = high or threats[:3]
        for t in focus[:3]:
            lines.append(f"- [ANALYSIS][{t['threat_level']}] {t['compressor_type']} {t['refrigerant']} {t['condition']} / {t['competitor']} / trust={t['trust_score']}")
        signals = analysis_bundle.get("new_signals", [])
        if signals:
            lines.append("")
            lines.append("### 신규/이상 신호")
            for s in signals[:5]:
                lines.append(f"- {s['signal_type']}: {s['description']} / trust={s['trust_score']}")
    else:
        high_first = sorted(evidence, key=lambda x: (x.threat_level != "high", not x.is_primary, -x.trust_score))[:3]
        if high_first:
            for item in high_first:
                low_note = " / 저신뢰 근거" if item.low_confidence else ""
                lines.append(f"- [{item.compressor_type}] {item.competitor}: {item.raw_text or item.summary} / 삼성 비교: {DISPLAY_STATUS[item.samsung_status]} / 위협도: {item.threat_level}{low_note}")
        else:
            lines.append("- 이번 주 확인된 고신뢰 근거 없음")
    lines.append("")
    lines.append("---")
    lines.append("")

    for ctype in ("Re", "Ro", "Sc"):
        lines.append(f"## {ctype} ({TYPE_LABELS[ctype]})")
        lines.append("")
        lines.append(f"### 삼성 {ctype} 경쟁 현황 스냅샷")
        ctype_items = [item for item in evidence if item.compressor_type == ctype]
        if ctype_items:
            summary = "; ".join(f"{item.competitor} {DISPLAY_STATUS[item.samsung_status]}" for item in ctype_items[:3])
            lines.append(f"- 이번 주 확인 사항: {summary}")
        else:
            lines.append("- 해당 없음 — 이번 주 확인된 고신뢰 근거 없음")
        lines.append("")
        for category in CATEGORIES:
            lines.append(f"### {category}")
            competitors_for_category = list(PRIMARY_COMPETITORS[ctype])
            for item in ctype_items:
                if item.category == category and item.competitor not in competitors_for_category:
                    competitors_for_category.append(item.competitor)
            for competitor in competitors_for_category:
                items = by_type_category_competitor.get((ctype, category, competitor), [])
                lines.append(f"#### {competitor}")
                if items:
                    for item in items:
                        low_note = "저신뢰 근거 — 단정 금지" if item.low_confidence else ""
                        lines.append(f"- 내용: {item.raw_text or item.summary}")
                        lines.append(f"  - 삼성 비교 관점: {DISPLAY_STATUS[item.samsung_status]}")
                        lines.append(f"  - 위협도/신뢰도: {item.threat_level} / {item.trust_score}{(' / ' + low_note) if low_note else ''}")
                        lines.append(f"  - 동적 태그: {', '.join(item.dynamic_tags)}")
                        lines.append(f"  - 출처: {item.source_name} / {item.source_date}")
                else:
                    lines.append(f"- 내용: {NO_EVIDENCE_TEXT}")
                    lines.append("  - 삼성 비교 관점: 확인 필요")
                    lines.append("  - 출처: 해당 없음")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## 삼성 Gap 종합 현황")
    lines.append("")
    lines.append("| 타입 | 조건/구간 | 냉매 | 경쟁사 보유 | 삼성 현황 | 위협도 |")
    lines.append("|---|---|---|---|---|---|")
    if analysis_bundle:
        for row in _gap_rows_from_analysis(analysis_bundle):
            lines.append(f"| {row['compressor_type']} | {row['condition']} | {row['refrigerant']} | {row['competitors']} | {DISPLAY_STATUS.get(row['samsung_status'], row['samsung_status'])} | {row['threat_level']} |")
    else:
        for row in _gap_rows(evidence):
            lines.append(f"| {row['compressor_type']} | {row['condition_or_capacity']} | {row['refrigerant']} | {row['competitor']} {row['product_or_series']} | {DISPLAY_STATUS.get(row['samsung_status'], row['samsung_status'])} | {row['threat_level']} |")
    if not evidence and not analysis_bundle:
        lines.append("| - | - | - | - | 확인 필요 | none |")
    lines.append("")
    lines.append("## 다음 주 모니터링 포인트")
    lines.append("- high/medium threat 및 신규 신호의 공식 출처 재검증")
    lines.append("- STEP 4에서 실제 Hermes Research Adapter 연결 검토")
    if feedback and feedback.get("required_fixes"):
        lines.append("- Critic 피드백 반영: " + "; ".join(feedback["required_fixes"]))
    lines.append("")
    lines.append("## 출처 목록")
    for source in _sources(evidence):
        lines.append(f"- [{source['source_name']}] {source['source_url']} / {source['source_date']} / {source['source_type']}")
    if not evidence:
        lines.append("- 해당 없음")
    lines.append("")
    lines.append(f"<!-- iteration: {iteration} -->")
    return "\n".join(lines)


def critique_step1_report(draft: str, evidence_dicts: list[dict[str, Any]], iteration: int = 0) -> dict[str, Any]:
    return critique_step_report(draft, evidence_dicts, iteration)


def critique_step_report(draft: str, evidence_dicts: list[dict[str, Any]], iteration: int = 0, *, analysis_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = [EvidenceItem(**item) for item in evidence_dicts]
    findings: list[str] = []
    fixes: list[str] = []
    hard_fail_reasons: list[str] = []
    score = 0
    structure_ok = all(f"## {ctype}" in draft for ctype in ("Re", "Ro", "Sc")) and all(f"### {cat}" in draft for cat in CATEGORIES)
    if structure_ok:
        score += 2
        findings.append("Re/Ro/Sc + 8개 카테고리 구조 준수")
    else:
        fixes.append("Re/Ro/Sc 모든 타입과 8개 카테고리를 빠짐없이 출력하세요.")
    if draft.count("삼성 비교 관점") >= 10 and all(status in draft for status in ("미보유", "대응 중", "확인 필요")):
        score += 2
        findings.append("삼성 비교 관점이 주요 항목에 반영됨")
    else:
        fixes.append("각 경쟁사 항목에 삼성 비교 관점과 추상 상태를 명시하세요.")
    gap_ok = "## 삼성 Gap 종합 현황" in draft and "| 타입 | 조건/구간 | 냉매 | 경쟁사 보유 | 삼성 현황 | 위협도 |" in draft
    if gap_ok:
        score += 2
        findings.append("Gap Matrix 표 포함")
    else:
        fixes.append("삼성 Gap Matrix 표를 생성하세요.")
    high_threats = (analysis_bundle or {}).get("threat_summary", []) if analysis_bundle else []
    has_high = any(t.get("threat_level") == "high" for t in high_threats) or any(item.threat_level == "high" for item in evidence)
    if not has_high or ("[ANALYSIS][high]" in draft or "위협도: high" in draft or "| high |" in draft):
        score += 1
        findings.append("high threat 핵심 동향 반영")
    else:
        fixes.append("high threat 항목을 핵심 동향 상단에 반영하세요.")
    if "## 출처 목록" in draft and ("manual://" in draft or "https://" in draft):
        score += 1
        findings.append("출처 목록 포함")
    else:
        fixes.append("출처 목록에 source name/url/date를 포함하세요.")
    missing_primary = []
    for ctype, competitors in PRIMARY_COMPETITORS.items():
        for competitor in competitors:
            if f"#### {competitor}" not in draft:
                missing_primary.append(f"{ctype}:{competitor}")
    if missing_primary:
        fixes.append("★ 최우선 경쟁사 누락: " + ", ".join(missing_primary))
    else:
        score += 2
        findings.append("★ 최우선 경쟁사 누락 없음")
    if not evidence:
        hard_fail_reasons.append("출처 0개")
    if analysis_bundle and not gap_ok:
        hard_fail_reasons.append("AnalysisBundle 있는데 Gap Matrix 표 누락")
    if analysis_bundle and has_high and "[ANALYSIS][high]" not in draft:
        hard_fail_reasons.append("high threat 항목 핵심 동향 미반영")
    if not any(f"## {ctype}" in draft for ctype in ("Re", "Ro", "Sc")):
        hard_fail_reasons.append("타입 전체 누락")
    if "삼성 비교 관점" not in draft:
        hard_fail_reasons.append("삼성 관점 전체 누락")
    primary_all_missing = all(f"#### {competitor}" not in draft for comps in PRIMARY_COMPETITORS.values() for competitor in comps)
    if primary_all_missing:
        hard_fail_reasons.append("★ 최우선 경쟁사 전체 누락")
    hard_fail = bool(hard_fail_reasons)
    return {"score": score, "passed": score >= PASS_SCORE and not hard_fail, "findings": findings, "required_fixes": fixes, "hard_fail": hard_fail, "hard_fail_reasons": hard_fail_reasons, "iteration": iteration}


def build_report_metadata(state: WorkflowState) -> ReportMetadata:
    evidence = [EvidenceItem(**item) for item in state.get("evidence", [])]
    week_id = state.get("week_id", evidence[0].week_id if evidence else "unknown")
    type_coverage = sorted({item.compressor_type for item in evidence})
    competitor_coverage = sorted({item.competitor for item in evidence})
    primary_missing = []
    for ctype, competitors in PRIMARY_COMPETITORS.items():
        for competitor in competitors:
            if not any(item.compressor_type == ctype and item.competitor == competitor for item in evidence):
                primary_missing.append(f"{ctype}:{competitor}")
    bundle = state.get("analysis_bundle") or {}
    signal_count = len(bundle.get("new_signals", [])) if isinstance(bundle, dict) else 0
    high_count = sum(1 for item in evidence if item.threat_level == "high")
    if isinstance(bundle, dict):
        high_count = max(high_count, sum(1 for item in bundle.get("threat_summary", []) if item.get("threat_level") == "high"))
    return ReportMetadata(week_id, state.get("run_date", "2026-06-25"), len(evidence), type_coverage, competitor_coverage, primary_missing, high_count, int(state.get("score", 0)), bool(state.get("hard_fail", False)), signal_count)


def _sources(evidence: list[EvidenceItem]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    sources: list[dict[str, str]] = []
    for item in evidence:
        key = (item.source_name, item.source_url, item.source_date)
        if key in seen:
            continue
        seen.add(key)
        sources.append({"source_name": item.source_name, "source_url": item.source_url, "source_date": item.source_date, "source_type": item.source_type})
    return sources


def _gap_rows(evidence: list[EvidenceItem]) -> list[dict[str, str]]:
    return [{"compressor_type": item.compressor_type, "condition_or_capacity": item.condition_or_capacity, "refrigerant": "/".join(item.refrigerant), "competitor": item.competitor, "product_or_series": item.product_or_series, "samsung_status": item.samsung_status, "threat_level": item.threat_level} for item in evidence]


def _gap_rows_from_analysis(bundle: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for ctype, refs in bundle.get("gap_matrix", {}).items():
        for ref, node in refs.items():
            if isinstance(node, dict) and "samsung" in node:
                cells = {"default": node}
            else:
                cells = node if isinstance(node, dict) else {}
            for condition, cell in cells.items():
                if not isinstance(cell, dict):
                    continue
                competitors = cell.get("competitors", [])
                if not competitors:
                    continue
                rows.append({"compressor_type": ctype, "condition": condition, "refrigerant": ref, "competitors": ", ".join(c.get("name", "") for c in competitors), "samsung_status": cell.get("samsung_status", cell.get("samsung", "확인필요")), "threat_level": cell.get("threat_level", "none")})
    return rows
