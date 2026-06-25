from __future__ import annotations

from typing import Protocol


class LLMAdapter(Protocol):
    """Interface only. Real Codex/Hermes calls live outside this repo."""

    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class StubLLMAdapter:
    """Deterministic STEP 1 stub. It never calls external APIs or reads secrets."""

    def generate(self, prompt: str) -> str:
        return prompt
