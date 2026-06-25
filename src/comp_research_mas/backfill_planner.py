from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from .agents import EVIDENCE_THRESHOLD, critique_step_report, get_period_context, write_step_report
from .analyst import build_analysis_bundle
from .evidence_normalizer import normalize_raw_results
from .memory_store import append_evidence_ledger, append_gap_history, read_gap_history
from .query_planner import build_query_plan, save_query_plan
from .research_adapter import HermesResearchAdapter, Step3StubResearchAdapter, save_raw_results
from .report_html import build_backfill_html, markdown_to_html

RESEARCH_PERIODS = [
    "2025-07", "2025-08", "2025-09",
    "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02", "2026-03",
    "2026-04", "2026-05", "2026-06",
]

DEFAULT_EVIDENCE_THRESHOLD = EVIDENCE_THRESHOLD["normal"]
EXHIBITION_CALENDAR_PATH = Path("config/exhibition_calendar.yaml")


def period_range(from_period: str, to_period: str, periods: list[str] | None = None) -> list[str]:
    periods = periods or RESEARCH_PERIODS
    return [period for period in periods if from_period <= period <= to_period]


def load_exhibition_calendar(path: str | Path = EXHIBITION_CALENDAR_PATH) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def boosted_sources_for_period(period: str, calendar: dict[str, Any] | None = None) -> list[str]:
    calendar = calendar or load_exhibition_calendar()
    month = int(period.split("-")[1])
    boosted: list[str] = []
    for event in calendar.values():
        if int(event.get("month", 0)) == month:
            boosted.extend(event.get("boost_sources", []))
    deduped: list[str] = []
    for source in boosted:
        if source not in deduped:
            deduped.append(source)
    return deduped


def build_backfill_plan(periods: list[str]) -> dict[str, Any]:
    period_plans: list[dict[str, Any]] = []
    for period in periods:
        boosts = boosted_sources_for_period(period)
        plan = build_query_plan("2026-26", period_id=period, source_boosts=boosts)
        for query in plan["queries"]:
            query["date_range"] = _period_date_range(period)
            query["keywords"] = _period_keywords(query, period)
        period_plans.append({"period_id": period, "period_context": get_period_context(period), "evidence_quality_threshold": EVIDENCE_THRESHOLD[get_period_context(period)], "source_boosts": boosts, "query_plan": plan})
    return {"periods": period_plans, "period_count": len(period_plans)}


def run_backfill(*, from_period: str = "2025-07", to_period: str = "2026-06", dry_run: bool = True, evidence_threshold: int = DEFAULT_EVIDENCE_THRESHOLD, injected_results_path: str | Path | None = None, show_query_plan: bool = False) -> dict[str, Any]:
    periods = period_range(from_period, to_period)
    plan = build_backfill_plan(periods)
    snapshots: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    previous_matrix: dict[str, Any] | None = None
    latest_matrix: dict[str, Any] = {}

    for period_item in plan["periods"]:
        period = period_item["period_id"]
        query_plan = period_item["query_plan"]
        save_query_plan(query_plan)
        if injected_results_path and len(plan["periods"]) == 1:
            raw_results = json.loads(Path(injected_results_path).read_text(encoding="utf-8"))
            raw_results = HermesResearchAdapter.validate_raw_results(raw_results, {**query_plan, "week_id": period, "period_id": period})
            raw_results["week_id"] = period
            raw_results["period_id"] = period
            _save_raw_results_for_period(raw_results)
        else:
            raw_results = Step3StubResearchAdapter().search(query_plan)
            if period.startswith("2025-"):
                raw_results["results"] = _thin_2025_stub_results(raw_results["results"])
            raw_results["week_id"] = period
            raw_results["period_id"] = period
            _save_raw_results_for_period(raw_results)
        evidence = normalize_raw_results(raw_results)
        threshold = EVIDENCE_THRESHOLD[get_period_context(period)] if evidence_threshold == DEFAULT_EVIDENCE_THRESHOLD else evidence_threshold
        evidence_quality = _evidence_quality(len(evidence), threshold)
        evidence_dicts = [_tag_evidence_quality(item.to_dict(), evidence_quality) for item in evidence]
        ledger_path = append_evidence_ledger(query_plan["week_id"], evidence_dicts, [{"node": "backfill", "step": "period research", "judgment": evidence_quality, "reasoning": f"evidence_count={len(evidence)} threshold={threshold}", "tool_used": False, "rag_used": False, "conclusion": period}], period_id=period)
        bundle = build_analysis_bundle(evidence, period)
        bundle_dict = bundle.to_dict()
        bundle_dict["period_id"] = period
        bundle_dict["evidence_quality"] = evidence_quality
        bundle_dict["evidence_count"] = len(evidence)
        _annotate_matrix_quality(bundle_dict["gap_matrix"], evidence_quality)
        period_output_paths = _write_period_outputs(period, evidence_dicts, bundle_dict)
        gap_path = append_gap_history(period, bundle_dict, [{"node": "backfill", "step": "gap snapshot", "judgment": evidence_quality, "reasoning": "period별 Gap Matrix 스냅샷 저장", "tool_used": False, "rag_used": False, "conclusion": period}], period_id=period)
        period_changes = _matrix_changes(previous_matrix, bundle_dict["gap_matrix"], previous_period=snapshots[-1]["period_id"] if snapshots else None, period=period)
        changes.extend(period_changes)
        previous_matrix = copy.deepcopy(bundle_dict["gap_matrix"])
        latest_matrix = copy.deepcopy(bundle_dict["gap_matrix"])
        snapshots.append({
            "period_id": period,
            "evidence_count": len(evidence),
            "evidence_quality": evidence_quality,
            "data_insufficient": evidence_quality == "data_insufficient",
            "source_boosts": period_item["source_boosts"],
            "period_context": get_period_context(period),
            "evidence_threshold_used": threshold,
            "gap_matrix": bundle_dict["gap_matrix"],
            "threat_count": len(bundle_dict.get("threat_summary", [])),
            "signal_count": len(bundle_dict.get("new_signals", [])),
            "ledger_path": str(ledger_path),
            "gap_history_path": str(gap_path),
            "output_paths": period_output_paths,
            "trust_distribution": dict(Counter(item.get("trust_score", 0) for item in evidence_dicts)),
            "critic_score": period_output_paths.get("critic_score"),
            "hard_fail": period_output_paths.get("hard_fail"),
        })

    summary = {
        "from_period": from_period,
        "to_period": to_period,
        "dry_run": dry_run,
        "period_snapshots": snapshots,
        "latest": {"period_id": snapshots[-1]["period_id"] if snapshots else None, "gap_matrix": latest_matrix},
        "state_changes": changes,
        "period_count": len(snapshots),
        "evidence_threshold": evidence_threshold,
        "dynamic_evidence_thresholds": EVIDENCE_THRESHOLD,
        "memory_periods": sorted(read_gap_history().get("periods", {}).keys()),
        "query_plan" if show_query_plan and len(plan["periods"]) == 1 else "query_plan_omitted": plan["periods"][0]["query_plan"] if show_query_plan and len(plan["periods"]) == 1 else True,
    }
    summary_path = Path("outputs/analysis/backfill_gap_summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = Path("outputs/reports/backfill_summary.md")
    html_report_path = Path("outputs/reports/backfill_summary.html")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_backfill_markdown(summary), encoding="utf-8")
    html_report_path.write_text(build_backfill_html(summary), encoding="utf-8")
    summary["output_paths"] = {"backfill_gap_summary": str(summary_path), "backfill_summary_report": str(report_path), "backfill_summary_html": str(html_report_path), "evidence_ledger": "outputs/memory/evidence_ledger.json", "gap_matrix_history": "outputs/memory/gap_matrix_history.json"}
    return summary



def _save_raw_results_for_period(raw_results: dict[str, Any]) -> Path:
    path = Path("outputs/search") / f"{raw_results['period_id']}_raw_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw_results, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_period_outputs(period: str, evidence_dicts: list[dict[str, Any]], bundle_dict: dict[str, Any]) -> dict[str, Any]:
    from .models import EvidenceItem
    items = [EvidenceItem(**_evidence_model_fields(item)) for item in evidence_dicts]
    directives: list[str] = []
    if bundle_dict.get("threat_summary"):
        directives.append("high threat 항목을 핵심 동향 최상단에 배치")
    if bundle_dict.get("new_signals"):
        directives.append("new_signals를 핵심 동향 별도 섹션에 배치")
    draft = write_step_report(items, analysis_bundle=bundle_dict, writer_directives=directives)
    review = critique_step_report(draft, [_evidence_model_fields(item) for item in evidence_dicts], analysis_bundle=bundle_dict)
    state = {
        "period_id": period,
        "week_id": period,
        "draft": draft,
        "evidence": evidence_dicts,
        "analysis_bundle": bundle_dict,
        "feedback": review,
        "score": review["score"],
        "hard_fail": review["hard_fail"],
        "sources": _sources_from_evidence_dicts(evidence_dicts),
    }
    report_dir = Path("outputs/reports")
    evidence_dir = Path("outputs/evidence")
    analysis_dir = Path("outputs/analysis")
    review_dir = Path("outputs/reviews")
    for directory in (report_dir, evidence_dir, analysis_dir, review_dir):
        directory.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{period}_compressor_monthly.md"
    html_path = report_dir / f"{period}_compressor_monthly.html"
    evidence_path = evidence_dir / f"{period}_evidence.json"
    analysis_path = analysis_dir / f"{period}_analysis_bundle.json"
    review_path = review_dir / f"{period}_critic_review.json"
    report_path.write_text(draft, encoding="utf-8")
    html_path.write_text(markdown_to_html(draft, state), encoding="utf-8")
    evidence_path.write_text(json.dumps({"period_id": period, "week_id": period, "evidence": evidence_dicts, "sources": state["sources"], "report_meta": {"total_evidence_count": len(evidence_dicts), "critic_score": review["score"], "hard_fail": review["hard_fail"]}}, ensure_ascii=False, indent=2), encoding="utf-8")
    analysis_path.write_text(json.dumps(bundle_dict, ensure_ascii=False, indent=2), encoding="utf-8")
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"report": str(report_path), "report_html": str(html_path), "evidence": str(evidence_path), "analysis": str(analysis_path), "review": str(review_path), "critic_score": review["score"], "hard_fail": review["hard_fail"], "rubric_breakdown": review.get("rubric_breakdown", {})}



def _evidence_model_fields(item: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "compressor_type", "competitor", "refrigerant", "category", "samsung_status",
        "trust_score", "source_type", "threat_level", "week_id", "period_id",
        "source_url", "source_date", "raw_text", "summary", "product_or_series",
        "condition_or_capacity", "application", "source_name", "is_primary",
        "low_confidence", "dynamic_tags", "evidence_id",
    }
    return {key: value for key, value in item.items() if key in allowed}

def _sources_from_evidence_dicts(evidence: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    sources: list[dict[str, str]] = []
    for item in evidence:
        key = (str(item.get("source_name", "")), str(item.get("source_url", "")), str(item.get("source_date", "")))
        if key in seen:
            continue
        seen.add(key)
        sources.append({"source_name": key[0], "source_url": key[1], "source_date": key[2], "source_type": str(item.get("source_type", ""))})
    return sources

def _period_date_range(period: str) -> dict[str, str]:
    year, month = period.split("-")
    end_day = {"01":"31","02":"29","03":"31","04":"30","05":"31","06":"30","07":"31","08":"31","09":"30","10":"31","11":"30","12":"31"}[month]
    return {"from": f"{period}-01", "to": f"{period}-{end_day}"}


def _period_keywords(query: dict[str, Any], period: str) -> list[str]:
    year, month_s = period.split("-")
    quarter = (int(month_s) - 1) // 3 + 1
    competitor = query["competitor"].replace("/", " ")
    ctype_term = {"Re": "reciprocating", "Ro": "rotary", "Sc": "scroll"}[query["compressor_type"]]
    refs = " ".join(query.get("refrigerants", [])[:2])
    base = list(query.get("keywords", []))
    base.extend([
        f"{competitor} {refs} {ctype_term} {period}",
        f"{competitor} {refs} {ctype_term} {year} Q{quarter}",
    ])
    return base


def _thin_2025_stub_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # 2025 H2는 실제 데이터가 부족한 dry-run 백필이라는 점을 보존한다.
    return results[:4]


def _evidence_quality(count: int, threshold: int) -> str:
    return "data_insufficient" if count < threshold else "sufficient"


def _tag_evidence_quality(item: dict[str, Any], quality: str) -> dict[str, Any]:
    tags = list(item.get("dynamic_tags", []))
    if quality == "data_insufficient" and "데이터 부족" not in tags:
        tags.append("데이터 부족")
        item["low_confidence"] = True
    item["dynamic_tags"] = tags
    item["period_evidence_quality"] = quality
    return item


def _annotate_matrix_quality(matrix: dict[str, Any], quality: str) -> None:
    for refs in matrix.values():
        if not isinstance(refs, dict):
            continue
        for node in refs.values():
            if not isinstance(node, dict):
                continue
            cells = {"default": node} if "samsung" in node or "samsung_status" in node else node
            for cell in cells.values():
                if isinstance(cell, dict):
                    cell["period_evidence_quality"] = quality
                    if quality == "data_insufficient":
                        cell["confidence_note"] = "데이터 부족 period 기반 — Gap Matrix 해석 시 낮은 신뢰도"


def _cell_statuses(matrix: dict[str, Any]) -> dict[tuple[str, str, str], str]:
    statuses: dict[tuple[str, str, str], str] = {}
    for ctype, refs in matrix.items():
        if not isinstance(refs, dict):
            continue
        for ref, node in refs.items():
            if not isinstance(node, dict):
                continue
            if "samsung" in node or "samsung_status" in node:
                statuses[(ctype, ref, "default")] = node.get("samsung_status") or node.get("samsung", "확인필요")
            else:
                for condition, cell in node.items():
                    if isinstance(cell, dict):
                        statuses[(ctype, ref, condition)] = cell.get("samsung_status") or cell.get("samsung", "확인필요")
    return statuses


def _matrix_changes(previous: dict[str, Any] | None, current: dict[str, Any], *, previous_period: str | None, period: str) -> list[dict[str, Any]]:
    if not previous:
        return []
    prev = _cell_statuses(previous)
    cur = _cell_statuses(current)
    changes: list[dict[str, Any]] = []
    for key, status in cur.items():
        before = prev.get(key)
        if before and before != status:
            ctype, ref, condition = key
            changes.append({"from_period": previous_period, "to_period": period, "compressor_type": ctype, "refrigerant": ref, "condition": condition, "from_status": before, "to_status": status})
    return changes


def _backfill_markdown(summary: dict[str, Any]) -> str:
    lines = ["# Backfill Gap Summary", "", f"기간: {summary['from_period']} ~ {summary['to_period']}", f"dry_run: {summary['dry_run']}", "", "## Period snapshots", "", "| period | evidence_count | quality | signals | threats |", "|---|---:|---|---:|---:|"]
    for snap in summary["period_snapshots"]:
        lines.append(f"| {snap['period_id']} | {snap['evidence_count']} | {snap['evidence_quality']} | {snap['signal_count']} | {snap['threat_count']} |")
    lines.extend(["", "## Latest", "", f"latest_period: {summary['latest']['period_id']}", "", "## State changes", ""])
    if not summary["state_changes"]:
        lines.append("- 상태 변화 없음 또는 dry-run stub 기준 동일")
    for change in summary["state_changes"]:
        lines.append(f"- {change['from_period']}→{change['to_period']} {change['compressor_type']}/{change['refrigerant']}/{change['condition']}: {change['from_status']}→{change['to_status']}")
    return "\n".join(lines) + "\n"
