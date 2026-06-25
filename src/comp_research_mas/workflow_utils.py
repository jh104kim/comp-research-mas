from __future__ import annotations

from typing import Any


def append_reasoning(state: dict[str, Any], *, node: str, step: str, reasoning: str, conclusion: str) -> list[dict[str, str]]:
    log = list(state.get("reasoning_log", []))
    log.append({"node": node, "step": step, "reasoning": reasoning, "conclusion": conclusion})
    return log
