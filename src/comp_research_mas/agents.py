from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import MAX_ITERATIONS, PASS_SCORE, REPORT_TITLE
from .models import CATEGORIES, NO_EVIDENCE_TEXT, PRIMARY_COMPETITORS, TYPE_LABELS, AnalysisBundle, EvidenceItem, ReportMetadata, SignalItem, ThreatItem, WorkflowState
from .tools import evidence_to_dicts, parse_step1_raw_data
from .rag import retrieve_related_evidence
from .memory_store import previous_report_text

DISPLAY_STATUS = {"보유": "보유", "미보유": "미보유", "대응중": "대응 중", "확인필요": "확인 필요"}


def load_raw_data_node(state: WorkflowState) -> WorkflowState:
    raw_data = state.get("raw_data", "")
    week_id = state.get("week_id", "2026-26")
    evidence = parse_step1_raw_data(raw_data, week_id=week_id)
    return {**state, "week_id": week_id, "evidence": evidence_to_dicts(evidence), "sources": _sources(evidence), "gap_table": _gap_rows(evidence), "iteration": int(state.get("iteration", 0)), "error_log": list(state.get("error_log", [])), "status": "loaded"}


def writer_node(state: WorkflowState) -> WorkflowState:
    evidence = [EvidenceItem(**item) for item in state.get("evidence", [])]
    debate_points = (state.get("feedback") or {}).get("debate_points", [])
    debate_decisions = decide_debate_points(debate_points)
    draft = write_step_report(evidence, analysis_bundle=state.get("analysis_bundle"), writer_directives=state.get("writer_directives", []), feedback=state.get("feedback"), iteration=int(state.get("iteration", 0)), debate_decisions=debate_decisions)
    from .workflow_utils import append_reasoning
    if not debate_points:
        judgment = "debate_not_needed"
    elif any(d["decision"] == "accepted" for d in debate_decisions):
        judgment = "debate_accepted"
    else:
        judgment = "debate_rejected"
    reasoning_log = append_reasoning(state, node="writer", step="RAG 기반 리포트 작성", reasoning="Evidence Ledger와 이전 리포트를 참조하고 debate_points를 검토해 작성 방향을 결정한다", judgment=judgment if debate_points else ("rag_reference" if evidence else "direct_write"), tool_used=False, rag_used=bool(evidence), persona_role="압축기 시장 인텔리전스 리포트 작성가", conclusion="draft 생성")
    return {**state, "draft": draft, "debate_decisions": debate_decisions, "reasoning_log": reasoning_log, "status": "drafted"}


def critic_node(state: WorkflowState) -> WorkflowState:
    previous_score = state.get("score")
    review = critique_step_report(state.get("draft", ""), state.get("evidence", []), int(state.get("iteration", 0)), analysis_bundle=state.get("analysis_bundle"))
    from .workflow_utils import append_reasoning
    comparison = "initial_score" if previous_score is None else ("improved" if review["score"] > int(previous_score) else "no_improvement")
    no_improvement = previous_score is not None and review["score"] <= int(previous_score) and int(state.get("iteration", 0)) > 0
    if no_improvement:
        review["human_review_flag"] = True
        review["hard_fail_reasons"].append("재작성 후 score 개선 없음")
    reasoning_log = append_reasoning(
        state,
        node="critic",
        step="품질 평가",
        reasoning="구조/삼성 비교/Gap Matrix/evidence/출처 신뢰도/최우선 경쟁사 커버리지를 10점 rubric으로 평가하고 재작성 전후 score를 비교",
        judgment=comparison,
        conclusion=f"score={review['score']}, previous_score={previous_score}, hard_fail={review['hard_fail']}, human_review_flag={review.get('human_review_flag', False)}",
    )
    writer_directives = list(state.get("writer_directives", []))
    for directive in review.get("writer_directives", []):
        if directive not in writer_directives:
            writer_directives.append(directive)
    return {
        **state,
        "score": review["score"],
        "feedback": review,
        "hard_fail": review["hard_fail"] or bool(review.get("human_review_flag")),
        "human_review_flag": bool(review.get("human_review_flag", False)),
        "writer_directives": writer_directives,
        "error_log": list(state.get("error_log", [])) + review["hard_fail_reasons"],
        "reasoning_log": reasoning_log,
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
    return write_step_report(evidence, feedback=feedback, iteration=iteration)


def write_step_report(evidence: list[EvidenceItem], *, analysis_bundle: dict[str, Any] | None = None, writer_directives: list[str] | None = None, feedback: dict[str, Any] | None = None, iteration: int = 0, debate_decisions: list[dict[str, Any]] | None = None) -> str:
    writer_directives = writer_directives or []
    debate_decisions = debate_decisions or []
    by_type_category_competitor: dict[tuple[str, str, str], list[EvidenceItem]] = defaultdict(list)
    for item in evidence:
        by_type_category_competitor[(item.compressor_type, item.category, item.competitor)].append(item)

    lines: list[str] = []
    lines.append(f"# {REPORT_TITLE}")
    lines.append(f"기간: {(analysis_bundle or {}).get('period_id') or (evidence[0].period_id if evidence else (analysis_bundle or {}).get('week_id', 'STEP SAMPLE'))}")
    lines.append("")
    lines.append("## 이번 달 핵심 동향 요약")
    prev_report = previous_report_text()
    if prev_report:
        lines.append("- 지난 달 대비 변화: 이전 리포트가 존재하여 Gap Matrix/신규 신호 중심으로 변화 항목을 우선 비교")
    if writer_directives:
        lines.append("- Orchestrator 지시: " + " / ".join(writer_directives))
    if debate_decisions:
        accepted = [d for d in debate_decisions if d["decision"] == "accepted"]
        rejected = [d for d in debate_decisions if d["decision"] == "rejected"]
        lines.append(f"- Debate 반영: accepted={len(accepted)}, rejected={len(rejected)}")
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
            lines.append(f"- 이번 달 확인 사항: {summary}")
        else:
            lines.append("- 해당 없음 — 이번 달 확인된 고신뢰 근거 없음")
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
                        related = retrieve_related_evidence(compressor_type=item.compressor_type, competitor=item.competitor, category=item.category)
                        ref_ids = [r.get("evidence_id") for r in related if r.get("evidence_id")]
                        if ref_ids:
                            lines.append(f"  - RAG 참조 evidence_ids: {', '.join(ref_ids[:3])}")
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
    lines.append("## 다음 달 모니터링 포인트")
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
    breakdown: dict[str, int] = {}
    writer_directives: list[str] = []

    structure_score, structure_fix = _score_structure(draft)
    breakdown["structure"] = structure_score
    score += structure_score
    if structure_score == 2:
        findings.append("Re/Ro/Sc + 8개 카테고리 구조 준수")
    else:
        fixes.append(structure_fix)
        writer_directives.append("Re/Ro/Sc 모든 타입과 8개 카테고리 섹션 재작성")

    samsung_score, samsung_fix = _score_samsung_comparison(draft, evidence)
    breakdown["samsung_comparison"] = samsung_score
    score += samsung_score
    if samsung_score == 3:
        findings.append("삼성 비교 관점이 최우선 경쟁사별 구체 상태와 위협도를 포함")
    else:
        fixes.append(samsung_fix)
        writer_directives.append("삼성 비교 관점: 최우선 경쟁사별 상태/위협도 보강")

    gap_score, gap_fix = _score_gap_matrix(draft)
    breakdown["gap_matrix"] = gap_score
    score += gap_score
    if gap_score == 2:
        findings.append("Gap Matrix에 Re/Ro/Sc, 냉매, 위협도 행 포함")
    else:
        fixes.append(gap_fix)
        writer_directives.append("삼성 Gap 종합 현황 표 재작성")

    evidence_score, evidence_fix = _score_evidence_quality(evidence)
    breakdown["evidence"] = evidence_score
    score += evidence_score
    if evidence_score == 1:
        findings.append("evidence_count >= 6 및 GMCC/LG/Copeland 근거 포함")
    else:
        fixes.append(evidence_fix)
        writer_directives.append("근거 부족: GMCC·LG·Copeland 최소 1개씩 재검색/보강")

    source_score, source_fix = _score_source_trust(evidence)
    breakdown["source_trust"] = source_score
    score += source_score
    if source_score == 1:
        findings.append("trust_score >= 4 출처 최소 2개 포함")
    else:
        fixes.append(source_fix)
        writer_directives.append("출처 목록: trust_score >= 4 공식/전시/학술/특허 출처 보강")

    primary_score, primary_fix = _score_primary_coverage(draft)
    breakdown["primary_competitor_coverage"] = primary_score
    score += primary_score
    if primary_score == 1:
        findings.append("GMCC·LG(Re/Ro) + Copeland(Sc) 실제 내용 포함")
    else:
        fixes.append(primary_fix)
        writer_directives.append("최우선 경쟁사 섹션: 해당 없음 외 실제 내용 보강")

    high_threats = (analysis_bundle or {}).get("threat_summary", []) if analysis_bundle else []
    has_high = any(t.get("threat_level") == "high" for t in high_threats) or any(item.threat_level == "high" for item in evidence)
    if analysis_bundle and has_high and "[ANALYSIS][high]" not in draft:
        hard_fail_reasons.append("high threat 항목 핵심 동향 미반영")
    if not evidence:
        hard_fail_reasons.append("출처 0개")
    if analysis_bundle and gap_score == 0:
        hard_fail_reasons.append("AnalysisBundle 있는데 Gap Matrix 표 누락")
    if not any(f"## {ctype}" in draft for ctype in ("Re", "Ro", "Sc")):
        hard_fail_reasons.append("타입 전체 누락")
    if "삼성 비교 관점" not in draft:
        hard_fail_reasons.append("삼성 관점 전체 누락")
    if primary_score == 0 and all(f"#### {competitor}" not in draft for comps in PRIMARY_COMPETITORS.values() for competitor in comps):
        hard_fail_reasons.append("★ 최우선 경쟁사 전체 누락")

    hard_fail = bool(hard_fail_reasons)
    debate_points = build_debate_points(score, fixes, hard_fail, breakdown=breakdown)
    return {
        "score": score,
        "passed": score >= PASS_SCORE and not hard_fail,
        "findings": findings,
        "required_fixes": fixes,
        "writer_directives": writer_directives,
        "debate_points": debate_points,
        "rubric_breakdown": breakdown,
        "hard_fail": hard_fail,
        "hard_fail_reasons": hard_fail_reasons,
        "iteration": iteration,
    }


def _score_structure(draft: str) -> tuple[int, str]:
    type_ok = all(f"## {ctype}" in draft for ctype in ("Re", "Ro", "Sc"))
    cats_ok = all(f"### {cat}" in draft for cat in CATEGORIES)
    if type_ok and cats_ok:
        return 2, ""
    return 0, "Re/Ro/Sc 모든 타입과 8개 카테고리를 빠짐없이 출력하세요."


def _score_samsung_comparison(draft: str, evidence: list[EvidenceItem]) -> tuple[int, str]:
    blocks = _primary_blocks(draft)
    concrete = 0
    partial = 0
    for key, block in blocks.items():
        has_real_evidence = _has_real_content(block)
        if not has_real_evidence and not any(item.competitor == key[1] and item.compressor_type == key[0] for item in evidence):
            continue
        has_status = any(status in block for status in ("미보유", "대응 중", "대응중", "보유", "확인 필요", "확인필요"))
        has_threat = "위협도" in block and any(level in block for level in ("high", "medium", "low", "none"))
        if "삼성 비교 관점" in block and has_status and has_threat and has_real_evidence:
            concrete += 1
        elif "삼성 비교 관점" in block:
            partial += 1
    total = sum(len(v) for v in PRIMARY_COMPETITORS.values())
    if concrete >= total:
        return 3, ""
    if concrete + partial >= max(1, total // 2):
        return 2, "최우선 경쟁사 일부가 누락되었거나 확인 필요 중심입니다."
    if "삼성 비교 관점" in draft:
        return 1, "삼성 비교 관점은 있으나 대부분 공란/해당없음입니다."
    return 0, "삼성 비교 관점 전체가 누락되었습니다."


def _score_gap_matrix(draft: str) -> tuple[int, str]:
    if "## 삼성 Gap 종합 현황" not in draft or "| 타입 | 조건/구간 | 냉매 | 경쟁사 보유 | 삼성 현황 | 위협도 |" not in draft:
        return 0, "Gap Matrix 누락 또는 빈 표입니다."
    rows = [line for line in draft.splitlines() if line.startswith("| ") and not line.startswith("| 타입") and not line.startswith("|---")]
    if not rows:
        return 0, "Gap Matrix 누락 또는 빈 표입니다."
    has_types = all(any(f"| {ctype} |" in row for row in rows) for ctype in ("Re", "Ro", "Sc"))
    has_ref = any("R290" in row or "R454B" in row or "R32" in row or "R600a" in row for row in rows)
    has_threat = any(any(level in row for level in ("high", "medium", "low", "none")) for row in rows)
    if has_types and has_ref and has_threat:
        return 2, ""
    return 1, "Gap Matrix에 일부 타입/냉매/위협도 행이 누락되었습니다."


def _score_evidence_quality(evidence: list[EvidenceItem]) -> tuple[int, str]:
    names = {item.competitor for item in evidence}
    ok_competitors = {"GMCC/Midea", "LG", "Copeland/Emerson"}.issubset(names)
    if len(evidence) >= 6 and ok_competitors:
        return 1, ""
    return 0, "evidence_count가 6 미만이거나 GMCC·LG·Copeland 근거가 부족합니다."


def _score_source_trust(evidence: list[EvidenceItem]) -> tuple[int, str]:
    high_sources = {(item.source_name, item.source_url) for item in evidence if item.trust_score >= 4}
    if len(high_sources) >= 2:
        return 1, ""
    return 0, "trust_score >= 4 출처가 2개 미만입니다."


def _score_primary_coverage(draft: str) -> tuple[int, str]:
    blocks = _primary_blocks(draft)
    required = [("Re", "GMCC/Midea"), ("Re", "LG"), ("Ro", "GMCC/Midea"), ("Ro", "LG"), ("Sc", "Copeland/Emerson")]
    for key in required:
        block = blocks.get(key, "")
        if not block or not _has_real_content(block):
            return 0, "최우선 경쟁사 중 1개 이상이 해당 없음만 포함합니다."
    return 1, ""



def _has_real_content(block: str) -> bool:
    for line in block.splitlines():
        if line.strip().startswith("- 내용:") and "해당 없음" not in line and "확인된 고신뢰 근거 없음" not in line:
            return True
    return False

def _primary_blocks(draft: str) -> dict[tuple[str, str], str]:
    blocks: dict[tuple[str, str], str] = {}
    current_type = ""
    lines = draft.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith("## ") and not line.startswith("###"):
            current_type = line.split()[1] if len(line.split()) > 1 else ""
        if line.startswith("#### "):
            competitor = line.replace("#### ", "", 1).strip()
            end = len(lines)
            for j in range(idx + 1, len(lines)):
                if lines[j].startswith("#### ") or lines[j].startswith("### ") or lines[j].startswith("## "):
                    end = j
                    break
            blocks[(current_type, competitor)] = blocks.get((current_type, competitor), "") + "\n" + "\n".join(lines[idx:end])
    return blocks


def build_debate_points(score: int, fixes: list[str], hard_fail: bool, *, breakdown: dict[str, int] | None = None) -> list[dict[str, str]]:
    if score >= 9 or not fixes:
        return []
    severity = "minor" if score >= 7 else "major"
    points: list[dict[str, str]] = []
    section_map = {
        "구조": "structure",
        "삼성": "samsung_comparison",
        "Gap Matrix": "gap_matrix",
        "evidence": "evidence",
        "출처": "sources",
        "trust_score": "sources",
        "최우선": "primary_competitor_coverage",
    }
    for fix in fixes:
        section = "report_quality"
        for token, mapped in section_map.items():
            if token in fix:
                section = mapped
                break
        points.append({
            "section": section,
            "issue": fix,
            "suggestion": f"{section} 섹션을 evidence/source 기준으로 보강",
            "severity": severity,
            "rubric_breakdown": str(breakdown or {}),
        })
    return points


def decide_debate_points(debate_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for point in debate_points:
        severity = point.get("severity", "minor")
        issue = point.get("issue", "")
        if severity == "major":
            decisions.append({**point, "decision": "accepted", "reason": "major 이슈는 품질 기준상 수용 우선"})
        elif "출처" in issue and "https://" not in issue:
            decisions.append({**point, "decision": "accepted", "reason": "출처 관련 minor 이슈는 보강 필요"})
        else:
            decisions.append({**point, "decision": "rejected", "reason": "minor 이슈이며 기존 evidence/구조로 설명 가능"})
    return decisions

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
    return ReportMetadata(week_id, state.get("run_date", "2026-06-25"), len(evidence), type_coverage, competitor_coverage, primary_missing, high_count, int(state.get("score", 0)), bool(state.get("hard_fail", False)), signal_count, state.get("period_id", week_id))


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
