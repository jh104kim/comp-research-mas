from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .agents import (
    critic_node,
    decide_after_critic,
    human_review_flag_node,
    increment_iteration_node,
    load_raw_data_node,
    writer_node,
)
from .models import WorkflowState
from .output import save_step1_outputs


def save_output_node(state: WorkflowState) -> WorkflowState:
    return save_step1_outputs(state)


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
    workflow.add_conditional_edges(
        "critic",
        decide_after_critic,
        {
            "save": "save_output",
            "rewrite": "increment_iteration",
            "human_review": "human_review_flag",
        },
    )
    workflow.add_edge("increment_iteration", "writer")
    workflow.add_edge("human_review_flag", "save_output")
    workflow.add_edge("save_output", END)
    return workflow.compile()


def run_step1(raw_data: str) -> WorkflowState:
    graph = build_step1_graph()
    return graph.invoke({"raw_data": raw_data, "iteration": 0, "error_log": []})
