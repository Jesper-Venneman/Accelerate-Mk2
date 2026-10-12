"""Tests for kathrena.agent_core.graph - the tool-calling agent loop (kathrena.agent_core.graph)."""

from __future__ import annotations

import dataclasses

from langchain_core.messages import AIMessage, HumanMessage

from kathrena.agent_core.graph import load_thread_messages, run_turn
from kathrena.rag_index.vector_store import SearchResult


def test_simple_reply_without_tool_calls(
    agent_config, fake_vector_store, scripted_chat_model
):
    model = scripted_chat_model([AIMessage(content="Hello there!")])

    result = run_turn(
        agent_config, fake_vector_store(), "thread-1", "hi", chat_model=model
    )

    assert result.reply == "Hello there!"
    assert len(model.invocations) == 1


def test_configured_system_prompt_reaches_the_model_alongside_the_tools_description(
    agent_config, fake_vector_store, scripted_chat_model
):
    """Decisions Log Round 31 - config.system_prompt is user-editable; the tool-availability
    sentence stays hardcoded regardless, so it can't drift out of sync with actual tools."""
    custom_config = dataclasses.replace(agent_config, system_prompt="Custom personality text.")
    model = scripted_chat_model([AIMessage(content="Hello there!")])

    run_turn(custom_config, fake_vector_store(), "thread-prompt", "hi", chat_model=model)

    system_message = model.invocations[-1][0]
    assert "Custom personality text." in system_message.content
    assert "search_vault" in system_message.content  # always-available tools description


def test_search_vault_tool_is_used_before_the_final_answer(
    agent_config, fake_vector_store, scripted_chat_model
):
    store = fake_vector_store(
        [SearchResult(content="Foo is a project about bar.", source_path="Foo/Foo.md")]
    )
    model = scripted_chat_model(
        [
            AIMessage(
                content="",
                tool_calls=[{"name": "search_vault", "args": {"query": "what is foo"}, "id": "1"}],
            ),
            AIMessage(content="Foo is a project about bar."),
        ]
    )

    result = run_turn(
        agent_config, store, "thread-2", "what is foo?", chat_model=model
    )

    assert result.reply == "Foo is a project about bar."
    assert store.queries == ["what is foo"]
    assert len(model.invocations) == 2
    second_call_messages = model.invocations[1]
    assert any("Foo is a project about bar." in str(m.content) for m in second_call_messages)


def test_read_vault_file_tool_is_used_before_the_final_answer(
    agent_config, fake_vector_store, scripted_chat_model
):
    agent_config.vault_root.mkdir(parents=True, exist_ok=True)
    (agent_config.vault_root / "Foo.md").write_text("Foo is a project about bar.", encoding="utf-8")
    model = scripted_chat_model(
        [
            AIMessage(
                content="",
                tool_calls=[{"name": "read_vault_file", "args": {"path": "Foo.md"}, "id": "1"}],
            ),
            AIMessage(content="Foo is a project about bar."),
        ]
    )

    result = run_turn(
        agent_config,
        fake_vector_store(),
        "thread-read-file",
        "what does Foo.md say?",
        chat_model=model,
    )

    assert result.reply == "Foo is a project about bar."


def test_reply_model_writes_the_final_answer_when_tool_and_reply_profiles_differ(
    agent_config, fake_vector_store, scripted_chat_model
):
    """When tool_profile != reply_profile, the tool-model's own draft (once it stops requesting
    tools) must never be shown - only the reply-model's own separate output should be."""
    split_config = dataclasses.replace(agent_config, tool_profile="local", reply_profile="cloud")
    store = fake_vector_store(
        [SearchResult(content="Foo is a project about bar.", source_path="Foo/Foo.md")]
    )
    tool_model = scripted_chat_model(
        [
            AIMessage(
                content="",
                tool_calls=[{"name": "search_vault", "args": {"query": "what is foo"}, "id": "1"}],
            ),
            AIMessage(content="tool-model's own draft - must never be shown"),
        ]
    )
    reply_model = scripted_chat_model([AIMessage(content="The actual final answer.")])

    result = run_turn(
        split_config,
        store,
        "thread-split",
        "what is foo?",
        chat_model=tool_model,
        reply_chat_model=reply_model,
    )

    assert result.reply == "The actual final answer."
    assert len(tool_model.invocations) == 2
    assert len(reply_model.invocations) == 1


def test_no_reply_model_call_when_tool_and_reply_profiles_match(
    agent_config, fake_vector_store, scripted_chat_model
):
    """The default (tool_profile == reply_profile) must behave exactly as before Round 28 - no
    extra node, no extra call."""
    model = scripted_chat_model([AIMessage(content="Hello there!")])

    result = run_turn(
        agent_config, fake_vector_store(), "thread-nosplit", "hi", chat_model=model
    )

    assert result.reply == "Hello there!"
    assert len(model.invocations) == 1


def test_history_window_caps_what_the_live_prompt_sends(
    agent_config, fake_vector_store, scripted_chat_model
):
    """Decisions Log Round 30 - the checkpointed history keeps growing, but a small enough
    `history_window_messages` must still trim what call_model actually sends the LLM."""
    windowed_config = dataclasses.replace(agent_config, history_window_messages=2)
    model = scripted_chat_model([AIMessage(content="first"), AIMessage(content="second")])

    run_turn(
        windowed_config, fake_vector_store(), "thread-window", "hello", chat_model=model
    )
    run_turn(
        windowed_config,
        fake_vector_store(),
        "thread-window",
        "hello again",
        chat_model=model,
    )

    last_call_contents = [getattr(m, "content", None) for m in model.invocations[-1]]
    assert "hello" not in last_call_contents  # trimmed out of the window
    assert "hello again" in last_call_contents  # still within the window


def test_load_thread_messages_returns_the_persisted_conversation(
    agent_config, fake_vector_store, scripted_chat_model
):
    model = scripted_chat_model([AIMessage(content="Hello there!")])
    run_turn(
        agent_config, fake_vector_store(), "thread-history", "hi", chat_model=model
    )

    messages = load_thread_messages(agent_config, "thread-history")

    assert [type(m) for m in messages] == [HumanMessage, AIMessage]
    assert messages[0].content == "hi"
    assert messages[1].content == "Hello there!"


def test_load_thread_messages_returns_empty_for_an_unknown_thread(agent_config):
    assert load_thread_messages(agent_config, "never-happened") == []


def test_search_memory_tool_is_used_before_the_final_answer(
    agent_config, fake_vector_store, fake_memory_provider, scripted_chat_model
):
    memory = fake_memory_provider(["The user prefers dark mode."])
    model = scripted_chat_model(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "search_memory", "args": {"query": "UI preferences"}, "id": "1"}
                ],
            ),
            AIMessage(content="You prefer dark mode."),
        ]
    )

    result = run_turn(
        agent_config,
        fake_vector_store(),
        "thread-5",
        "what are my UI preferences?",
        memory_provider=memory,
        chat_model=model,
    )

    assert result.reply == "You prefer dark mode."
    assert memory.queries == ["UI preferences"]


def test_remember_is_scheduled_with_the_full_conversation_after_a_turn(
    agent_config, fake_vector_store, fake_memory_provider, scripted_chat_model
):
    memory = fake_memory_provider()
    model = scripted_chat_model([AIMessage(content="Hello there!")])

    run_turn(
        agent_config,
        fake_vector_store(),
        "thread-6",
        "hi",
        memory_provider=memory,
        chat_model=model,
    )

    assert len(memory.remembered) == 1
    messages, thread_id = memory.remembered[0]
    assert thread_id == "thread-6"
    assert any(getattr(m, "content", None) == "hi" for m in messages)
    assert any(getattr(m, "content", None) == "Hello there!" for m in messages)


def test_remember_receives_the_whole_thread_not_just_the_latest_turn(
    agent_config, fake_vector_store, fake_memory_provider, scripted_chat_model
):
    memory = fake_memory_provider()
    model = scripted_chat_model(
        [AIMessage(content="First reply."), AIMessage(content="Second reply.")]
    )
    store = fake_vector_store()

    run_turn(
        agent_config,
        store,
        "thread-7",
        "first",
        memory_provider=memory,
        chat_model=model,
    )
    run_turn(
        agent_config,
        store,
        "thread-7",
        "second",
        memory_provider=memory,
        chat_model=model,
    )

    assert len(memory.remembered) == 2
    second_call_messages = memory.remembered[1][0]
    # The second remember() call should see both turns, not just the latest one.
    contents = [getattr(m, "content", None) for m in second_call_messages]
    assert "first" in contents
    assert "First reply." in contents
    assert "second" in contents
    assert "Second reply." in contents


def test_no_memory_provider_means_no_remember_calls(
    agent_config, fake_vector_store, scripted_chat_model
):
    model = scripted_chat_model([AIMessage(content="Hello there!")])

    result = run_turn(
        agent_config, fake_vector_store(), "thread-8", "hi", chat_model=model
    )

    assert result.reply == "Hello there!"  # no memory_provider given - nothing to assert beyond
    # not crashing; there's no memory object here to check "remembered" against, by design.


def test_get_current_datetime_tool_is_always_available(
    agent_config, fake_vector_store, scripted_chat_model
):
    """Unlike search_memory/list_deadlines/search_web, get_current_datetime needs no optional
    collaborator - it should work even when every other new capability is left at its default."""
    model = scripted_chat_model(
        [
            AIMessage(
                content="",
                tool_calls=[{"name": "get_current_datetime", "args": {}, "id": "1"}],
            ),
            AIMessage(content="It's Tuesday."),
        ]
    )

    result = run_turn(
        agent_config, fake_vector_store(), "thread-9", "what day is it?",
        chat_model=model,
    )

    assert result.reply == "It's Tuesday."


def test_list_deadlines_tool_is_used_when_pm_config_is_given(
    agent_config, fake_vector_store, pm_config, scripted_chat_model
):
    pm_config.vault_root.mkdir(parents=True)
    (pm_config.vault_root / "Report.md").write_text(
        "---\ndue: 2026-09-05\n---\n", encoding="utf-8"
    )
    model = scripted_chat_model(
        [
            AIMessage(
                content="",
                tool_calls=[{"name": "list_deadlines", "args": {}, "id": "1"}],
            ),
            AIMessage(content="Report.md is due soon."),
        ]
    )

    result = run_turn(
        agent_config,
        fake_vector_store(),
        "thread-10",
        "any close deadlines?",
        pm_config=pm_config,
        chat_model=model,
    )

    assert result.reply == "Report.md is due soon."
    second_call_messages = model.invocations[1]
    assert any("Report.md" in str(m.content) for m in second_call_messages)


def test_no_pm_config_means_no_list_deadlines_tool(
    agent_config, fake_vector_store, scripted_chat_model
):
    model = scripted_chat_model([AIMessage(content="Hello there!")])

    result = run_turn(
        agent_config, fake_vector_store(), "thread-11", "hi", chat_model=model
    )

    assert result.reply == "Hello there!"


def test_search_web_tool_is_used_when_web_search_is_given(
    agent_config, fake_vector_store, fake_web_search, scripted_chat_model
):
    from kathrena.agent_core.web_search import SearchHit

    web_search = fake_web_search(
        [SearchHit(title="Foo News", url="https://example.com/foo", snippet="Foo happened.")]
    )
    model = scripted_chat_model(
        [
            AIMessage(
                content="",
                tool_calls=[{"name": "search_web", "args": {"query": "foo news"}, "id": "1"}],
            ),
            AIMessage(content="Foo happened, per the news."),
        ]
    )

    result = run_turn(
        agent_config,
        fake_vector_store(),
        "thread-12",
        "what's new with foo?",
        web_search=web_search,
        chat_model=model,
    )

    assert result.reply == "Foo happened, per the news."
    assert web_search.queries == ["foo news"]


def test_no_web_search_means_no_search_web_tool(
    agent_config, fake_vector_store, scripted_chat_model
):
    model = scripted_chat_model([AIMessage(content="Hello there!")])

    result = run_turn(
        agent_config, fake_vector_store(), "thread-13", "hi", chat_model=model
    )

    assert result.reply == "Hello there!"
