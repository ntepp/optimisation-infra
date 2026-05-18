from __future__ import annotations

from typing import Callable


class NullLLMProvider:
    """
    Test double for LLMProvider. Returns scripted payloads.

    Use one of:
    - `NullLLMProvider(payload={...})`           — fixed payload for every call
    - `NullLLMProvider(payloads=[{...}, ...])`   — queue of payloads, consumed in order
    - `NullLLMProvider(handler=lambda s, u: ...)` — programmatic per-call response
    """

    def __init__(
        self,
        payload: dict | list | None = None,
        payloads: list[dict | list] | None = None,
        handler: Callable[[str, str], dict | list] | None = None,
    ):
        self._payload = payload
        self._payloads = list(payloads) if payloads else None
        self._handler = handler
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str) -> dict | list:
        self.calls.append((system, user))

        if self._handler is not None:
            return self._handler(system, user)

        if self._payloads is not None:
            if not self._payloads:
                raise RuntimeError("NullLLMProvider: queue of payloads exhausted")
            return self._payloads.pop(0)

        if self._payload is not None:
            return self._payload

        return {}
