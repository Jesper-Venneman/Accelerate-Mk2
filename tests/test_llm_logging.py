"""Tests for kathrena.llm_logging - plain-text LLM/tool call logging (Decisions Log Round 32)."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult, LLMResult

from kathrena.llm_logging import LoggingCallbackHandler, log_tool_call, with_logging


class _FakeBoundableChatModel(BaseChatModel):
    """A real `BaseChatModel` (not a bare stand-in) with a working `bind_tools` - needed to
    reproduce the actual bug `with_logging` guards against: `RunnableBindingBase.__getattr__`
    forwards `bind_tools` straight to the *unbound* underlying model, silently dropping an
    earlier `.with_config(callbacks=[...])` unless it's applied after `bind_tools`, not before.
    """

    @property
    def _llm_type(self) -> str:
        return "fake-boundable"

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=tools, **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Hello there!"))])


def test_log_tool_call_writes_input_and_output(tmp_path):
    path = tmp_path / "llm_calls.log"

    log_tool_call("agent_core", "search_vault", {"query": "foo"}, "No relevant notes found.", path=path)

    text = path.read_text(encoding="utf-8")
    assert "[agent_core] TOOL search_vault IN: {'query': 'foo'}" in text
    assert "[agent_core] TOOL search_vault OUT: 'No relevant notes found.'" in text


def test_logging_callback_handler_writes_llm_input_and_output(tmp_path):
    path = tmp_path / "llm_calls.log"
    handler = LoggingCallbackHandler("agent_core.tool", path=path)

    handler.on_chat_model_start(
        {}, [[HumanMessage(content="hi")]], run_id="00000000-0000-0000-0000-000000000000"
    )
    handler.on_llm_end(
        LLMResult(generations=[[ChatGeneration(message=AIMessage(content="Hello there!"))]]),
        run_id="00000000-0000-0000-0000-000000000000",
    )

    text = path.read_text(encoding="utf-8")
    assert "[agent_core.tool] LLM IN: human: 'hi'" in text
    assert "[agent_core.tool] LLM OUT: 'Hello there!'" in text


def test_logging_callback_handler_logs_tool_calls_when_content_is_empty(tmp_path):
    path = tmp_path / "llm_calls.log"
    handler = LoggingCallbackHandler("agent_core.tool", path=path)

    message = AIMessage(
        content="",
        tool_calls=[{"name": "search_vault", "args": {"query": "foo"}, "id": "1"}],
    )
    handler.on_llm_end(
        LLMResult(generations=[[ChatGeneration(message=message)]]),
        run_id="00000000-0000-0000-0000-000000000000",
    )

    text = path.read_text(encoding="utf-8")
    assert "tool_calls: search_vault({'query': 'foo'})" in text


def test_different_labels_share_one_log_file(tmp_path):
    path = tmp_path / "llm_calls.log"

    log_tool_call("agent_core", "get_current_datetime", {}, "Monday", path=path)
    log_tool_call("memory", "search_memory", {"query": "x"}, "nothing", path=path)

    text = path.read_text(encoding="utf-8")
    assert "[agent_core] TOOL get_current_datetime" in text
    assert "[memory] TOOL search_memory" in text


def test_with_logging_applied_after_bind_tools_still_logs(tmp_path):
    model = _FakeBoundableChatModel()

    model_with_tools = with_logging(model.bind_tools([]), "agent_core.tool")
    model_with_tools.invoke([HumanMessage(content="hi")])

    text = (tmp_path / "llm_calls.log").read_text(encoding="utf-8")
    assert "[agent_core.tool] LLM IN: human: 'hi'" in text
    assert "[agent_core.tool] LLM OUT: 'Hello there!'" in text


def test_with_logging_applied_before_bind_tools_is_silently_dropped(tmp_path):
    model = _FakeBoundableChatModel()

    model_with_tools = with_logging(model, "agent_core.tool").bind_tools([])
    model_with_tools.invoke([HumanMessage(content="hi")])

    log_path = tmp_path / "llm_calls.log"
    assert not log_path.exists() or log_path.read_text(encoding="utf-8") == ""
