from src.adapters.outbound.llm.null_provider import NullLLMProvider
from src.adapters.outbound.llm.openai_provider import _extract_json_block, _strip_fences


def test_strip_fences_removes_json_fence():
    assert _strip_fences("```json\n{\"a\": 1}\n```") == '{"a": 1}'


def test_strip_fences_removes_generic_fence():
    assert _strip_fences("```\n[1,2,3]\n```") == "[1,2,3]"


def test_strip_fences_no_change_when_no_fence():
    assert _strip_fences('{"a": 1}') == '{"a": 1}'


def test_extract_json_block_finds_object_in_prose():
    text = "Sure, here is the answer: {\"a\": 1}\nLet me know if…"
    assert _extract_json_block(text) == '{"a": 1}'


def test_extract_json_block_finds_array():
    assert _extract_json_block("Result: [1, 2, 3]. Done.") == "[1, 2, 3]"


def test_null_llm_returns_default_payload():
    null = NullLLMProvider(payload={"recommendations": []})
    out = null.complete_json("sys", "user")
    assert out == {"recommendations": []}


def test_null_llm_consumes_queue_in_order():
    null = NullLLMProvider(payloads=[{"step": 1}, {"step": 2}])
    assert null.complete_json("a", "b") == {"step": 1}
    assert null.complete_json("a", "b") == {"step": 2}


def test_null_llm_handler_takes_precedence():
    null = NullLLMProvider(payload={"x": 1}, handler=lambda s, u: {"y": 2})
    assert null.complete_json("a", "b") == {"y": 2}


def test_null_llm_records_calls():
    null = NullLLMProvider(payload={})
    null.complete_json("sys-1", "usr-1")
    null.complete_json("sys-2", "usr-2")
    assert null.calls == [("sys-1", "usr-1"), ("sys-2", "usr-2")]
