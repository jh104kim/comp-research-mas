from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .research_adapter import HermesResearchAdapter, ResearchAdapter, Step3StubResearchAdapter
from .workflow_utils import append_reasoning


class HermesLiveAdapter(ResearchAdapter):
    """
    헤르메스가 자율 판단하여 연결 방식 선택:
      A: injected JSON 파일 로드
      B: 외부 runner placeholder
    실패 시 Step3StubResearchAdapter fallback.
    """

    def __init__(self, injected_results_path: str | None = None, fallback_to_stub: bool = True):
        self.injected_results_path = injected_results_path or os.environ.get("HERMES_RAW_RESULTS_PATH")
        self.fallback_to_stub = fallback_to_stub
        self.last_decision: dict[str, Any] = {}

    def search(self, query_plan: dict[str, Any]) -> dict[str, Any]:
        try:
            if self.injected_results_path and Path(self.injected_results_path).exists():
                self.last_decision = {"mode": "injected_json", "reason": "injected_results_path exists", "path": self.injected_results_path}
                return HermesResearchAdapter(self.injected_results_path, fallback_to_stub=False).search(query_plan)
            # External runner direct-call integration point. Repo never performs web/search itself.
            runner_enabled = os.environ.get("HERMES_EXTERNAL_RUNNER_READY") == "1"
            if runner_enabled:
                self.last_decision = {"mode": "external_runner_placeholder", "reason": "runner flag set but repo has no network/search implementation"}
                raise RuntimeError("External runner must inject raw_results into repo boundary")
            if self.fallback_to_stub:
                self.last_decision = {"mode": "stub_fallback", "reason": "no injected JSON or external runner available"}
                return Step3StubResearchAdapter().search(query_plan)
            raise RuntimeError("No Hermes live adapter path available")
        except Exception as exc:
            if not self.fallback_to_stub:
                raise
            self.last_decision = {"mode": "stub_fallback", "reason": f"live path failed: {exc}"}
            return Step3StubResearchAdapter().search(query_plan)


def hermes_live_adapter_node(state: dict[str, Any]) -> dict[str, Any]:
    adapter = HermesLiveAdapter(injected_results_path=state.get("injected_results_path"), fallback_to_stub=True)
    raw_results = adapter.search(state["query_plan"])
    from .research_adapter import save_raw_results
    save_raw_results(raw_results)
    decision = adapter.last_decision
    reasoning_log = append_reasoning(
        state,
        node="hermes_live_adapter",
        step="Hermes 실제 검색 연결 방식 선택",
        judgment=decision.get("mode", "unknown"),
        reasoning=decision.get("reason", ""),
        tool_used=True,
        rag_used=False,
        persona_role="HVACR 시장 정보 수집 전문가",
        conclusion="raw_results 생성",
    )
    return {**state, "raw_results": raw_results, "hermes_live_decision": decision, "reasoning_log": reasoning_log, "status": "researched_step6"}
