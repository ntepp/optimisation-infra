from __future__ import annotations

import json
import re


def _strip_fences(content: str) -> str:
    """Strip markdown code fences that GPT-4o often wraps JSON responses in."""
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    return content.strip()


def _extract_json_block(content: str) -> str:
    """Last-resort: locate the outermost {...} or [...] block in case of trailing prose."""
    text = _strip_fences(content)
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]
    return text


class OpenAIProvider:
    """
    Adapter around langchain_openai.ChatOpenAI exposing the LLMProvider port.

    Encapsulates:
    - System+human prompt assembly
    - Markdown fence cleanup
    - JSON parsing
    - One retry on JSONDecodeError, asking the model to "respond with valid JSON only"
    """

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.0, api_key: str | None = None):
        from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]
        kwargs: dict = {"model": model, "temperature": temperature}
        if api_key:
            kwargs["api_key"] = api_key
        self._llm = ChatOpenAI(**kwargs)

    def complete_json(self, system: str, user: str) -> dict | list:
        from langchain_core.messages import SystemMessage, HumanMessage  # type: ignore[import-not-found]

        response = self._llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=user),
        ])
        raw = response.content if hasattr(response, "content") else str(response)

        try:
            return json.loads(_strip_fences(raw))
        except json.JSONDecodeError:
            pass

        try:
            return json.loads(_extract_json_block(raw))
        except json.JSONDecodeError:
            pass

        retry = self._llm.invoke([
            SystemMessage(content=system + " Reply with valid JSON ONLY, no prose."),
            HumanMessage(content=user + "\n\nYour previous answer was not valid JSON. Reply with strict JSON only."),
        ])
        retry_raw = retry.content if hasattr(retry, "content") else str(retry)
        return json.loads(_extract_json_block(retry_raw))
