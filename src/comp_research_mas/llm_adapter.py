from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import asdict, dataclass
from typing import Protocol

from .env_utils import load_root_env


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


class OpenAIAdapter(StubLLMAdapter):
    provider = "openai"

    def _call_or_dry(self, operation: str, prompt: str) -> str:
        load_root_env()
        live = os.environ.get("COMP_RESEARCH_LLM_LIVE", "0") == "1"
        api_key = os.environ.get("OPENAI_API_KEY")
        if not live or not api_key:
            return json.dumps(LLMCallLog(self.provider, True, operation, len(prompt), "openai dry-run; set COMP_RESEARCH_LLM_LIVE=1 for live call").to_dict(), ensure_ascii=False)
        # Minimal Responses API call. Never logs the API key.
        payload = json.dumps({
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            "input": prompt,
            "max_output_tokens": 300,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec - fixed OpenAI endpoint
            data = json.loads(resp.read().decode("utf-8"))
        text = data.get("output_text") or json.dumps(data, ensure_ascii=False)[:1000]
        return text

    def generate_report(self, prompt: str) -> str:
        return self._call_or_dry("generate_report", prompt)

    def critique_report(self, prompt: str) -> str:
        return self._call_or_dry("critique_report", prompt)

    def debate(self, prompt: str) -> str:
        return self._call_or_dry("debate", prompt)


class CodexAdapter(OpenAIAdapter):
    provider = "codex"


# Backward-compatible alias; new config should use openai.
ClaudeAdapter = OpenAIAdapter


def get_llm_adapter(provider: str | None = None) -> LLMAdapter:
    load_root_env()
    name = (provider or os.environ.get("COMP_RESEARCH_LLM_PROVIDER") or "stub").lower()
    if name in {"openai", "claude"}:
        return OpenAIAdapter()
    if name == "codex":
        return CodexAdapter()
    return StubLLMAdapter()


def llm_dry_run(provider: str | None = None) -> dict[str, object]:
    adapter = get_llm_adapter(provider)
    result = adapter.generate_report("compressor MAS dry-run prompt")
    return {"provider": getattr(adapter, "provider", "unknown"), "dry_run": True, "result": result}
