from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .agents import critic_node, decide_after_critic, human_review_flag_node, increment_iteration_node, load_raw_data_node, writer_node
from .analyst import build_analysis_bundle, orchestrator_directives, save_analysis_bundle
from .evidence_normalizer import normalize_raw_results
from .memory_store import append_evidence_ledger, append_gap_history
from .models import EvidenceItem, WorkflowState
from .output import save_step_outputs
from .query_planner import build_query_plan, replan_query_plan, save_query_plan
from .research_adapter import HermesResearchAdapter, Step3StubResearchAdapter, StubResearchAdapter, save_raw_results
from .workflow_utils import append_reasoning
from .guardian import guardian_node
from .notifier import notifier_node

EVIDENCE_REPLAN_THRESHOLD = 8


def save_output_node(state: WorkflowState) -> WorkflowState:
    reasoning_log = append_reasoning(state, node="save_output", step="산출물 저장", reasoning="report/review/evidence/analysis/memory 경로를 저장한다", conclusion="최종 output_paths 생성")
    return save_step_outputs({**state, "reasoning_log": reasoning_log})


def build_step1_graph():
    workflow = StateGraph(WorkflowState)
    workflow.add_node("load_raw_data", load_raw_data_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("increment_iteration", increment_iteration_node)
    workflow.add_node("human_review_flag", human_review_flag_node)
    workflow.add_node("save_output", save_output_node)
    workflow.add_edge(START, "load_raw_data")
    workflow.add_edge("load_raw_data", "writer")
    workflow.add_edge("writer", "critic")
    workflow.add_conditional_edges("critic", decide_after_critic, {"save": "save_output", "rewrite": "increment_iteration", "human_review": "human_review_flag"})
    workflow.add_edge("increment_iteration", "writer")
    workflow.add_edge("human_review_flag", "save_output")
    workflow.add_edge("save_output", END)
    return workflow.compile()


def source_planner_node(state: WorkflowState) -> WorkflowState:
    week_id = state.get("week_id", "2026-26")
    reasoning_log = append_reasoning(state, node="source_planner", step="query plan 생성", reasoning="타입×경쟁사×카테고리 기준으로 최우선 경쟁사 query를 먼저 만든다", conclusion=f"week_id={week_id} query_plan 생성")
    period_id = state.get("period_id", week_id)
    query_plan = build_query_plan(week_id, period_id=period_id)
    save_query_plan(query_plan)
    return {**state, "week_id": week_id, "period_id": period_id, "query_plan": query_plan, "reasoning_log": reasoning_log, "status": "query_planned"}


def research_adapter_node(state: WorkflowState) -> WorkflowState:
    reasoning_log = append_reasoning(state, node="research_adapter", step="stub 검색 실행", reasoning="STEP 5 전까지 실제 Hermes 검색 대신 deterministic stub 결과를 사용한다", conclusion="raw_results 생성")
    raw_results = StubResearchAdapter().search(state["query_plan"])
    save_raw_results(raw_results)
    return {**state, "raw_results": raw_results, "reasoning_log": reasoning_log, "status": "researched"}


def step3_research_adapter_node(state: WorkflowState) -> WorkflowState:
    reasoning_log = append_reasoning(state, node="research_adapter", step="STEP3 stub 검색 실행", reasoning="이상 신호 트리거용 stub 데이터를 포함하되 실제 검색은 STEP 5로 미룬다", conclusion="STEP3 raw_results 생성")
    raw_results = Step3StubResearchAdapter().search(state["query_plan"])
    save_raw_results(raw_results)
    return {**state, "raw_results": raw_results, "reasoning_log": reasoning_log, "status": "researched_step3"}


def evidence_normalizer_node(state: WorkflowState) -> WorkflowState:
    evidence = normalize_raw_results(state["raw_results"])
    reasoning_log = append_reasoning(state, node="evidence_normalizer", step="raw_results 정규화", reasoning=f"raw result를 EvidenceItem으로 변환하고 중복 제거한다. evidence_count={len(evidence)}", conclusion="evidence 생성")
    # Dynamic replanning: if coverage is low, broaden query plan and rerun stub research once.
    if len(evidence) < EVIDENCE_REPLAN_THRESHOLD and not state.get("query_plan", {}).get("replanned"):
        replanned = replan_query_plan(state["query_plan"], evidence_count=len(evidence), threshold=EVIDENCE_REPLAN_THRESHOLD)
        save_query_plan(replanned)
        adapter = Step3StubResearchAdapter() if state.get("status") == "researched_step3" else StubResearchAdapter()
        raw_results = adapter.search(replanned)
        save_raw_results(raw_results)
        evidence = normalize_raw_results(raw_results)
        reasoning_log = append_reasoning({**state, "reasoning_log": reasoning_log}, node="source_planner", step="동적 재계획", reasoning=f"evidence_count가 {EVIDENCE_REPLAN_THRESHOLD} 미만이라 primary query를 확장하고 재실행", conclusion=f"replanned evidence_count={len(evidence)}")
        state = {**state, "query_plan": replanned, "raw_results": raw_results, "replan_count": int(state.get("replan_count", 0)) + 1}
    evidence_dicts = [item.to_dict() for item in evidence]
    ledger_path = append_evidence_ledger(state.get("week_id", "2026-26"), evidence_dicts, reasoning_log, period_id=state.get("period_id"))
    reasoning_log = append_reasoning({**state, "reasoning_log": reasoning_log}, node="memory", step="Evidence Ledger append", reasoning="주차별 evidence를 outputs/memory/evidence_ledger.json에 누적 저장", conclusion=str(ledger_path))
    return {**state, "evidence": evidence_dicts, "sources": _sources_from_evidence(evidence_dicts), "gap_table": _gap_from_evidence(evidence_dicts), "evidence_ledger_path": str(ledger_path), "reasoning_log": reasoning_log, "status": "evidence_normalized"}


def analyst_node(state: WorkflowState) -> WorkflowState:
    evidence = [EvidenceItem(**item) for item in state.get("evidence", [])]
    if not evidence:
        reasoning_log = append_reasoning(state, node="analyst", step="fallback 판단", reasoning="AnalysisBundle 생성에 필요한 evidence가 없다", conclusion="evidence_normalizer fallback")
        return {**state, "analysis_bundle": None, "writer_directives": ["AnalysisBundle empty: evidence fallback"], "reasoning_log": reasoning_log, "status": "analysis_fallback"}
    reasoning_log = append_reasoning(state, node="analyst", step="Gap Matrix 분석", reasoning="EvidenceItem[]과 baseline/history를 교차 분석해 threat와 signal을 산출한다", conclusion="AnalysisBundle 생성")
    bundle = build_analysis_bundle(evidence, state.get("week_id", "2026-26"))
    analysis_path = save_analysis_bundle(bundle)
    gap_history_path = append_gap_history(bundle.week_id, bundle.to_dict(), reasoning_log, period_id=state.get("period_id"))
    directives = orchestrator_directives(bundle)
    reasoning_log = append_reasoning({**state, "reasoning_log": reasoning_log}, node="memory", step="Gap history append", reasoning="주차별 Gap Matrix를 outputs/memory/gap_matrix_history.json에 누적 저장", conclusion=str(gap_history_path))
    return {**state, "analysis_bundle": bundle.to_dict(), "writer_directives": directives, "analysis_path": str(analysis_path), "gap_history_path": str(gap_history_path), "reasoning_log": reasoning_log, "status": "analyzed"}



def step5_research_adapter_node(state: WorkflowState) -> WorkflowState:
    adapter = HermesResearchAdapter(injected_results_path=state.get("injected_results_path"), fallback_to_stub=True)
    raw_results = adapter.search(state["query_plan"])
    save_raw_results(raw_results)
    dist = HermesResearchAdapter.trust_distribution(raw_results)
    judgment = "additional_search_needed" if dist["high_confidence"] < 3 else "sufficient_sources"
    reasoning_log = append_reasoning(
        state,
        node="research_adapter",
        step="Hermes adapter 주입/검증/fallback",
        reasoning=f"고신뢰 결과 {dist['high_confidence']}건 / 전체 {dist['total']}건. 실제 검색 호출은 repo 밖에서 수행",
        judgment=judgment,
        tool_used=True,
        rag_used=False,
        persona_role="HVACR 시장 정보 수집 전문가",
        conclusion="raw_results 생성",
    )
    return {**state, "raw_results": raw_results, "research_trust_distribution": dist, "reasoning_log": reasoning_log, "status": "researched_step5"}


def notifier_dry_run_node(state: WorkflowState) -> WorkflowState:
    return notifier_node(state)


def decide_after_step5_critic(state: WorkflowState) -> str:
    guardian = state.get("guardian_result") or {}
    if state.get("hard_fail") or guardian.get("severity") == "block":
        return "human_review"
    if int(state.get("score", 0)) >= 9 and not state.get("human_review_flag"):
        return "notify"
    if int(state.get("score", 0)) >= 7 and not state.get("human_review_flag"):
        return "notify"
    if int(state.get("iteration", 0)) < 2 and (state.get("feedback") or {}).get("debate_points"):
        return "rewrite"
    return "human_review"

def build_step2_graph():
    workflow = StateGraph(WorkflowState)
    workflow.add_node("source_planner", source_planner_node)
    workflow.add_node("research_adapter", research_adapter_node)
    workflow.add_node("evidence_normalizer", evidence_normalizer_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("increment_iteration", increment_iteration_node)
    workflow.add_node("human_review_flag", human_review_flag_node)
    workflow.add_node("save_output", save_output_node)
    workflow.add_edge(START, "source_planner")
    workflow.add_edge("source_planner", "research_adapter")
    workflow.add_edge("research_adapter", "evidence_normalizer")
    workflow.add_edge("evidence_normalizer", "writer")
    workflow.add_edge("writer", "critic")
    workflow.add_conditional_edges("critic", decide_after_critic, {"save": "save_output", "rewrite": "increment_iteration", "human_review": "human_review_flag"})
    workflow.add_edge("increment_iteration", "writer")
    workflow.add_edge("human_review_flag", "save_output")
    workflow.add_edge("save_output", END)
    return workflow.compile()


def build_step3_graph():
    workflow = StateGraph(WorkflowState)
    workflow.add_node("source_planner", source_planner_node)
    workflow.add_node("research_adapter", step3_research_adapter_node)
    workflow.add_node("evidence_normalizer", evidence_normalizer_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("increment_iteration", increment_iteration_node)
    workflow.add_node("human_review_flag", human_review_flag_node)
    workflow.add_node("save_output", save_output_node)
    workflow.add_edge(START, "source_planner")
    workflow.add_edge("source_planner", "research_adapter")
    workflow.add_edge("research_adapter", "evidence_normalizer")
    workflow.add_edge("evidence_normalizer", "analyst")
    workflow.add_edge("analyst", "writer")
    workflow.add_edge("writer", "critic")
    workflow.add_conditional_edges("critic", decide_after_critic, {"save": "save_output", "rewrite": "increment_iteration", "human_review": "human_review_flag"})
    workflow.add_edge("increment_iteration", "writer")
    workflow.add_edge("human_review_flag", "save_output")
    workflow.add_edge("save_output", END)
    return workflow.compile()



def build_step5_graph():
    workflow = StateGraph(WorkflowState)
    workflow.add_node("source_planner", source_planner_node)
    workflow.add_node("research_adapter", step5_research_adapter_node)
    workflow.add_node("guardian_after_research", guardian_node)
    workflow.add_node("evidence_normalizer", evidence_normalizer_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("guardian_after_writer", guardian_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("increment_iteration", increment_iteration_node)
    workflow.add_node("human_review_flag", human_review_flag_node)
    workflow.add_node("notifier_dry_run", notifier_dry_run_node)
    workflow.add_node("guardian_before_save", guardian_node)
    workflow.add_node("save_output", save_output_node)
    workflow.add_edge(START, "source_planner")
    workflow.add_edge("source_planner", "research_adapter")
    workflow.add_edge("research_adapter", "guardian_after_research")
    workflow.add_edge("guardian_after_research", "evidence_normalizer")
    workflow.add_edge("evidence_normalizer", "analyst")
    workflow.add_edge("analyst", "writer")
    workflow.add_edge("writer", "guardian_after_writer")
    workflow.add_edge("guardian_after_writer", "critic")
    workflow.add_conditional_edges("critic", decide_after_step5_critic, {"notify": "notifier_dry_run", "rewrite": "increment_iteration", "human_review": "human_review_flag"})
    workflow.add_edge("increment_iteration", "writer")
    workflow.add_edge("human_review_flag", "guardian_before_save")
    workflow.add_edge("notifier_dry_run", "guardian_before_save")
    workflow.add_edge("guardian_before_save", "save_output")
    workflow.add_edge("save_output", END)
    return workflow.compile()

def run_step1(raw_data: str) -> WorkflowState:
    return build_step1_graph().invoke({"raw_data": raw_data, "week_id": "2026-26", "iteration": 0, "error_log": [], "reasoning_log": []})


def run_step2(week_id: str = "2026-26") -> WorkflowState:
    return build_step2_graph().invoke({"week_id": week_id, "iteration": 0, "error_log": [], "reasoning_log": []})


def run_step3(week_id: str = "2026-26", period_id: str | None = None) -> WorkflowState:
    return build_step3_graph().invoke({"week_id": week_id, "period_id": period_id or week_id, "iteration": 0, "error_log": [], "reasoning_log": []})


def run_step5(period_id: str = "2026-06", injected_results_path: str | None = None, approve_send: bool = False) -> WorkflowState:
    return build_step5_graph().invoke({"week_id": "2026-26", "period_id": period_id, "injected_results_path": injected_results_path, "approve_send": approve_send, "iteration": 0, "error_log": [], "reasoning_log": []})


def _sources_from_evidence(evidence: list[dict]) -> list[dict]:
    return [{"source_name": item["source_name"], "source_url": item["source_url"], "source_date": item["source_date"], "source_type": item["source_type"]} for item in evidence]


def _gap_from_evidence(evidence: list[dict]) -> list[dict]:
    return [{"compressor_type": item["compressor_type"], "condition_or_capacity": item["condition_or_capacity"], "refrigerant": "/".join(item["refrigerant"]), "competitor": item["competitor"], "product_or_series": item["product_or_series"], "samsung_status": item["samsung_status"], "threat_level": item["threat_level"]} for item in evidence]
