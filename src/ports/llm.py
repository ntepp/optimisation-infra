from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """
    LLM port. Implementations: OpenAI, Anthropic, NullLLM (tests), local stub.

    `complete_json` is the only method use-cases need: send system+user prompts,
    receive parsed JSON (dict or list). The adapter handles cleanup of markdown
    fences, JSON parsing, and at most one retry on invalid JSON.
    """

    def complete_json(self, system: str, user: str) -> dict | list: ...
