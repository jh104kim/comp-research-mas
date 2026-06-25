from __future__ import annotations

from typing import Any


def append_reasoning(
    state: dict[str, Any],
    *,
    node: str,
    step: str,
    reasoning: str = "",
    conclusion: str,
    judgment: str = "proceed",
    tool_used: bool = False,
    rag_used: bool = False,
) -> list[dict[str, Any]]:
    log = list(state.get("reasoning_log", []))
    log.append(
        {
            "node": node,
            "step": step,
            "judgment": judgment,
            "reasoning": reasoning,
            "tool_used": tool_used,
            "rag_used": rag_used,
            "conclusion": conclusion,
        }
    )
    return log
