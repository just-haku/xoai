from types import SimpleNamespace

from xoai.agents.base import _normalize_tool_calls, _parse_tool_call


def test_normalize_tool_calls_wraps_single_provider_call():
    call = SimpleNamespace(name="lookup", args={"q": "xoai"})
    assert _normalize_tool_calls(call) == [call]
    assert _normalize_tool_calls(None) == []


def test_parse_tool_call_supports_openai_shape():
    call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="lookup", arguments='{"q": "xoai"}'),
    )
    name, args, tc_id = _parse_tool_call(call)
    assert name == "lookup"
    assert args == {"q": "xoai"}
    assert tc_id == "call-1"


def test_parse_tool_call_supports_gemini_shape():
    call = SimpleNamespace(name="lookup", args={"q": "xoai"})
    name, args, tc_id = _parse_tool_call(call)
    assert name == "lookup"
    assert args == {"q": "xoai"}
    assert tc_id == "lookup"


def test_parse_tool_call_supports_dict_shape():
    call = {"id": "call-2", "function": {"name": "lookup", "arguments": '{"q": "xoai"}'}}
    name, args, tc_id = _parse_tool_call(call)
    assert name == "lookup"
    assert args == {"q": "xoai"}
    assert tc_id == "call-2"
