from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .agents import critic_node, decide_after_critic, human_review_flag_node, increment_iteration_node, load_raw_data_node, writer_node
from .evidence_normalizer import normalize_raw_results
from .models import WorkflowState
from .output import save_step_outputs
from .query_planner import build_query_plan, save_query_plan
from .research_adapter import StubResearchAdapter, save_raw_results


def save_output_node(state: WorkflowState) -> WorkflowState:
    return save_step_outputs(state)


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
    query_plan = build_query_plan(week_id)
    save_query_plan(query_plan)
    return {**state, "week_id": week_id, "query_plan": query_plan, "status": "query_planned"}


def research_adapter_node(state: WorkflowState) -> WorkflowState:
    raw_results = StubResearchAdapter().search(state["query_plan"])
    save_raw_results(raw_results)
    return {**state, "raw_results": raw_results, "status": "researched"}


def evidence_normalizer_node(state: WorkflowState) -> WorkflowState:
    evidence = normalize_raw_results(state["raw_results"])
    evidence_dicts = [item.to_dict() for item in evidence]
    return {**state, "evidence": evidence_dicts, "sources": _sources_from_evidence(evidence_dicts), "gap_table": _gap_from_evidence(evidence_dicts), "status": "evidence_normalized"}


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


def run_step1(raw_data: str) -> WorkflowState:
    return build_step1_graph().invoke({"raw_data": raw_data, "week_id": "2026-26", "iteration": 0, "error_log": []})


def run_step2(week_id: str = "2026-26") -> WorkflowState:
    return build_step2_graph().invoke({"week_id": week_id, "iteration": 0, "error_log": []})


def _sources_from_evidence(evidence: list[dict]) -> list[dict]:
    return [{"source_name": item["source_name"], "source_url": item["source_url"], "source_date": item["source_date"], "source_type": item["source_type"]} for item in evidence]


def _gap_from_evidence(evidence: list[dict]) -> list[dict]:
    return [{"compressor_type": item["compressor_type"], "condition_or_capacity": item["condition_or_capacity"], "refrigerant": "/".join(item["refrigerant"]), "competitor": item["competitor"], "product_or_series": item["product_or_series"], "samsung_status": item["samsung_status"], "threat_level": item["threat_level"]} for item in evidence]
