from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Protocol


class LLMAdapter(Protocol):
    def generate_report(self, prompt: str) -> str: ...
    def critique_report(self, prompt: str) -> str: ...
    def debate(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class LLMCallLog:
    provider: str
    dry_run: bool
    operation: str
    prompt_chars: int
    result_preview: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class StubLLMAdapter:
    """Deterministic adapter. It never calls external APIs or reads secrets."""

    provider = "stub"

    def generate(self, prompt: str) -> str:
        return prompt

    def generate_report(self, prompt: str) -> str:
        return prompt

    def critique_report(self, prompt: str) -> str:
        return "stub critique: 구조/근거 검토 완료"

    def debate(self, prompt: str) -> str:
        return "stub debate: critic 지적을 writer directive로 반영"


class ClaudeAdapter(StubLLMAdapter):
    provider = "claude"

    def _dry(self, operation: str, prompt: str) -> str:
        return json.dumps(LLMCallLog(self.provider, True, operation, len(prompt), "dry-run only; set approval gate for live call").to_dict(), ensure_ascii=False)

    def generate_report(self, prompt: str) -> str:
        return self._dry("generate_report", prompt)

    def critique_report(self, prompt: str) -> str:
        return self._dry("critique_report", prompt)

    def debate(self, prompt: str) -> str:
        return self._dry("debate", prompt)


class CodexAdapter(ClaudeAdapter):
    provider = "codex"


def get_llm_adapter(provider: str | None = None) -> LLMAdapter:
    name = (provider or os.environ.get("COMP_RESEARCH_LLM_PROVIDER") or "stub").lower()
    if name == "claude":
        return ClaudeAdapter()
    if name == "codex":
        return CodexAdapter()
    return StubLLMAdapter()


def llm_dry_run(provider: str | None = None) -> dict[str, object]:
    adapter = get_llm_adapter(provider)
    result = adapter.generate_report("compressor MAS dry-run prompt")
    return {"provider": getattr(adapter, "provider", "unknown"), "dry_run": True, "result": result}
