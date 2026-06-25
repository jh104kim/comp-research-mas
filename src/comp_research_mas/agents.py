from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import MAX_ITERATIONS, PASS_SCORE, REPORT_TITLE
from .models import (
    CATEGORIES,
    NO_EVIDENCE_TEXT,
    PRIMARY_COMPETITORS,
    SECONDARY_COMPETITORS,
    TYPE_LABELS,
    EvidenceItem,
    WorkflowState,
)
from .tools import evidence_to_dicts, parse_step1_raw_data


def load_raw_data_node(state: WorkflowState) -> WorkflowState:
    raw_data = state.get("raw_data", "")
    evidence = parse_step1_raw_data(raw_data)
    return {
        **state,
        "evidence": evidence_to_dicts(evidence),
        "sources": _sources(evidence),
        "gap_table": _gap_rows(evidence),
        "iteration": int(state.get("iteration", 0)),
        "error_log": list(state.get("error_log", [])),
        "status": "loaded",
    }


def writer_node(state: WorkflowState) -> WorkflowState:
    evidence = [EvidenceItem(**item) for item in state.get("evidence", [])]
    draft = write_step1_report(evidence, feedback=state.get("feedback"), iteration=int(state.get("iteration", 0)))
    return {**state, "draft": draft, "status": "drafted"}


def critic_node(state: WorkflowState) -> WorkflowState:
    review = critique_step1_report(state.get("draft", ""), state.get("evidence", []), int(state.get("iteration", 0)))
    return {
        **state,
        "score": review["score"],
        "feedback": review,
        "hard_fail": review["hard_fail"],
        "error_log": list(state.get("error_log", [])) + review["hard_fail_reasons"],
        "status": "reviewed",
    }


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
    by_type_category_competitor: dict[tuple[str, str, str], list[EvidenceItem]] = defaultdict(list)
    for item in evidence:
        by_type_category_competitor[(item.compressor_type, item.category, item.competitor)].append(item)

    lines: list[str] = []
    lines.append(f"# {REPORT_TITLE}")
    lines.append("날짜: STEP 1 SAMPLE")
    lines.append("")
    lines.append("## 이번 주 핵심 동향 요약")
    top = evidence[:3]
    if top:
        for item in top:
            lines.append(f"- [{item.compressor_type}] {item.competitor}: {item.summary} / 삼성 비교: {item.samsung_status}")
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
            summary = "; ".join(f"{item.competitor} {item.samsung_status}" for item in ctype_items[:3])
            lines.append(f"- 이번 주 확인 사항: {summary}")
        else:
            lines.append("- 해당 없음 — 이번 주 확인된 고신뢰 근거 없음")
        lines.append("")

        competitors_to_show = list(PRIMARY_COMPETITORS[ctype])
        for item in ctype_items:
            if item.competitor not in competitors_to_show:
                competitors_to_show.append(item.competitor)
        # Secondary competitors are shown only when evidence exists.
        competitors_to_show = [c for c in competitors_to_show if c in PRIMARY_COMPETITORS[ctype] or any(i.competitor == c for i in ctype_items)]

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
                        lines.append(f"- 내용: {item.summary}")
                        lines.append(f"  - 삼성 비교 관점: {item.samsung_status}")
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
    for row in _gap_rows(evidence):
        lines.append(
            f"| {row['compressor_type']} | {row['condition_or_capacity']} | {row['refrigerant']} | {row['competitor']} {row['product_or_series']} | {row['samsung_status']} | {row['threat_level']} |"
        )
    if not evidence:
        lines.append("| - | - | - | - | 확인 필요 | 낮음 |")
    lines.append("")
    lines.append("## 다음 주 모니터링 포인트")
    lines.append("- ★ 최우선 경쟁사 중 `해당 없음`으로 남은 항목의 공식 출처 확인")
    lines.append("- 삼성 비교 상태가 `확인 필요`인 항목을 내부 매핑 없이 공개 정보 기준으로 재검증")
    lines.append("- STEP 2에서 Source Planner/Search Agent가 수집할 query registry로 전환")
    if feedback and feedback.get("required_fixes"):
        lines.append("- Critic 피드백 반영: " + "; ".join(feedback["required_fixes"]))
    lines.append("")
    lines.append("## 출처 목록")
    for source in _sources(evidence):
        lines.append(f"- [{source['source_name']}] {source['source_url']} / {source['source_date']}")
    if not evidence:
        lines.append("- 해당 없음")
    lines.append("")
    lines.append(f"<!-- iteration: {iteration} -->")
    return "\n".join(lines)


def critique_step1_report(draft: str, evidence_dicts: list[dict[str, Any]], iteration: int = 0) -> dict[str, Any]:
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

    samsung_count = draft.count("삼성 비교 관점")
    if samsung_count >= 10 and all(status in draft for status in ("미보유", "대응 중", "확인 필요")):
        score += 3
        findings.append("삼성 비교 관점이 주요 항목에 반영됨")
    else:
        fixes.append("각 경쟁사 항목에 삼성 비교 관점과 추상 상태를 명시하세요.")

    if "## 삼성 Gap 종합 현황" in draft and "| 타입 | 조건/구간 | 냉매 | 경쟁사 보유 | 삼성 현황 | 위협도 |" in draft:
        score += 2
        findings.append("삼성 Gap 표 구조 포함")
    else:
        fixes.append("삼성 Gap 종합 현황 표를 생성하세요.")

    if "## 출처 목록" in draft and ("manual://" in draft or "출처:" in draft or " / 202" in draft):
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
    if not any(f"## {ctype}" in draft for ctype in ("Re", "Ro", "Sc")):
        hard_fail_reasons.append("타입 전체 누락")
    if "삼성 비교 관점" not in draft:
        hard_fail_reasons.append("삼성 관점 전체 누락")
    primary_all_missing = all(f"#### {competitor}" not in draft for comps in PRIMARY_COMPETITORS.values() for competitor in comps)
    if primary_all_missing:
        hard_fail_reasons.append("★ 최우선 경쟁사 전체 누락")

    hard_fail = bool(hard_fail_reasons)
    return {
        "score": score,
        "passed": score >= PASS_SCORE and not hard_fail,
        "findings": findings,
        "required_fixes": fixes,
        "hard_fail": hard_fail,
        "hard_fail_reasons": hard_fail_reasons,
        "iteration": iteration,
    }


def _sources(evidence: list[EvidenceItem]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    sources: list[dict[str, str]] = []
    for item in evidence:
        key = (item.source_name, item.source_url, item.source_date)
        if key in seen:
            continue
        seen.add(key)
        sources.append({"source_name": item.source_name, "source_url": item.source_url, "source_date": item.source_date})
    return sources


def _gap_rows(evidence: list[EvidenceItem]) -> list[dict[str, str]]:
    rows = []
    for item in evidence:
        threat = "높음" if item.samsung_status == "미보유" and item.is_primary else "중간" if item.samsung_status in {"미보유", "확인 필요"} else "낮음"
        rows.append(
            {
                "compressor_type": item.compressor_type,
                "condition_or_capacity": item.condition_or_capacity,
                "refrigerant": item.refrigerant,
                "competitor": item.competitor,
                "product_or_series": item.product_or_series,
                "samsung_status": item.samsung_status,
                "threat_level": threat,
            }
        )
    return rows
