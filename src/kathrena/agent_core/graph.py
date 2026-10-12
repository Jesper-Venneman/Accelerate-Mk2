"""LangGraph plumbing for Module G: a tool-calling conversational agent for Kathrena.

Design spec: Architecture/Modules/G - Kathrena Agent Core.md

A hand-rolled ReAct-style loop (call_model -> call_tools -> call_model -> ... -> END), matching
the explicit-graph style used by `kathrena.rag_index.indexer` rather than `langgraph.prebuilt`'s
`create_react_agent`, so the tool-calling loop stays as inspectable as the rest of this codebase.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated, Any, TypedDict

from kathrena.agent_core.config import AgentCoreConfig
from kathrena.agent_core.tools import (
    build_change_setting_tool,
    build_current_datetime_tool,
    build_list_deadlines_tool,
    build_read_vault_file_tool,
    build_search_memory_tool,
    build_search_vault_tool,
    build_set_llm_mode_tool,
    build_web_search_tool,
)
from kathrena.agent_core.web_search import WebSearch
from kathrena.memory import MemoryProvider
from kathrena.project_management import ProjectManagementConfig
from kathrena.rag_index.vector_store import VectorStore

# Describes tools that are always registered, merged with system prompt later.
_TOOLS_SYSTEM_PROMPT_ADDITION = (
    "\n\nYou have these tools: `search_vault` to look up relevant notes before answering questions "
    "about the user's projects, `read_vault_file` to read more of a note around an excerpt "
    "search_vault surfaced (pass that exact excerpt as near_text) or a note's full contents if "
    "you don't have one, "
    "`get_current_datetime` for the current local date/time, since you have no other sense of "
    "\"now\", `set_llm_mode` to switch every LLM-using role between local/cloud/standard in one "
    "call (e.g. to free up the GPU), and `change_setting` to change a single one of those "
    "settings instead."
)

# System prompt additions for optional tools.
_MEMORY_SYSTEM_PROMPT_ADDITION = (
    " You also have `search_memory` to recall facts, preferences, or past conversations about the "
    "user that aren't in the vault."
)
_DEADLINES_SYSTEM_PROMPT_ADDITION = (
    " You also have `list_deadlines` to check for vault notes with an upcoming or overdue due "
    "date - only use it when asked about deadlines/due dates, don't bring it up unprompted."
)
_WEB_SEARCH_SYSTEM_PROMPT_ADDITION = (
    " You also have `search_web` to search the public internet for anything current or not in "
    "the vault or memory."
)


class AgentState(TypedDict):
    messages: Annotated[list[Any], operator.add]


@dataclass(frozen=True)
class TurnResult:
    """What Kathrena said, plus any change she proposed during this specific turn."""

    reply: str


def build_agent_graph(
    config: AgentCoreConfig,
    vector_store: VectorStore,
    memory_provider: MemoryProvider | None = None,
    pm_config: ProjectManagementConfig | None = None,
    web_search: WebSearch | None = None,
    chat_model: Any | None = None,
    reply_chat_model: Any | None = None,
):
    """Build the (uncompiled) tool-calling agent graph. Compile with a checkpointer to run it."""
    # Imported lazily so importing this module doesn't require langgraph/langchain-openai unless
    # a graph is actually built.
    from langchain_core.messages import SystemMessage, ToolMessage, trim_messages
    from langchain_core.runnables import RunnableConfig
    from langchain_core.tools import tool as _as_tool
    from langgraph.graph import END, START, StateGraph

    system_prompt = config.system_prompt + _TOOLS_SYSTEM_PROMPT_ADDITION

    # Add the always-available tools... wrapped as proper LangChain tools (not plain functions)
    # so invoking them below goes through the Runnable protocol - that's what lets a callback
    # handler like cl.LangchainCallbackHandler() see tool calls at all (Decisions Log Round 32).
    tools = [_as_tool(build_search_vault_tool(vector_store, config.rag_top_k)), # Search Vault tool
             # Read Vault File tool
             _as_tool(build_read_vault_file_tool(config.vault_root, config.read_file_max_chars)), 
             # Current DateTime tool
             _as_tool(build_current_datetime_tool()), 
             # LLM mode switch tool
             _as_tool(build_set_llm_mode_tool()), 
             # Individual setting change tool
             _as_tool(build_change_setting_tool()),
             ]

    # Add optional tools based on the provided collaborators...
    if memory_provider is not None: # Memory tool
        tools.append(_as_tool(build_search_memory_tool(memory_provider)))
        system_prompt += _MEMORY_SYSTEM_PROMPT_ADDITION
    if pm_config is not None: # Project Management tool
        tools.append(_as_tool(build_list_deadlines_tool(pm_config)))
        system_prompt += _DEADLINES_SYSTEM_PROMPT_ADDITION
    if web_search is not None: # Web Search tool
        tools.append(_as_tool(build_web_search_tool(web_search, config.web_search_max_results)))
        system_prompt += _WEB_SEARCH_SYSTEM_PROMPT_ADDITION
    tools_by_name = {tool.name: tool for tool in tools}

    built_chat_model = chat_model is None
    if chat_model is None:
        from kathrena.llm import build_chat_model, resolve_profile

        chat_model = build_chat_model(resolve_profile(config.tool_profile))
    model_with_tools = chat_model.bind_tools(tools)
    if built_chat_model:
        from kathrena.llm_logging import with_logging

        model_with_tools = with_logging(model_with_tools, "agent_core.tool")

    # If the two profiles differ, a second, non-tool-bound model writes the reply actually shown
    # once the tool-calling loop is done (Decisions Log Round 28) - when they're equal (the
    # default), this whole block is skipped and the graph behaves exactly as it always has.
    split = config.tool_profile != config.reply_profile
    if split and reply_chat_model is None:
        from kathrena.llm import build_chat_model, resolve_profile
        from kathrena.llm_logging import with_logging

        reply_chat_model = with_logging(
            build_chat_model(resolve_profile(config.reply_profile)), "agent_core.reply"
        )

    def _windowed_prompt(state: AgentState) -> list:
        """The system prompt plus a capped tail of the thread's messages (Decisions Log Round 30)."""
        trimmed = trim_messages(
            state["messages"],
            strategy="last",
            token_counter=len,
            max_tokens=config.history_window_messages,
            start_on="human",
        )
        return [SystemMessage(content=system_prompt), *trimmed]

    def call_model(state: AgentState, config: RunnableConfig) -> dict:
        response = model_with_tools.invoke(_windowed_prompt(state), config=config)
        return {"messages": [response]}

    def call_tools(state: AgentState, config: RunnableConfig) -> dict:
        from kathrena.llm_logging import log_tool_call

        last = state["messages"][-1]
        tool_messages = []
        for call in last.tool_calls:
            tool_obj = tools_by_name.get(call["name"])
            if tool_obj is None:
                content = f"Unknown tool: {call['name']}"
            else:
                try:
                    result = tool_obj.invoke(call["args"], config=config)
                except Exception as exc:  # tool failures go back to the model, not the user
                    content = f"Tool error: {exc}"
                    log_tool_call("agent_core", call["name"], call["args"], content)
                else:
                    content = str(result)
                    log_tool_call("agent_core", call["name"], call["args"], result)
            tool_messages.append(ToolMessage(content=content, tool_call_id=call["id"]))
        return {"messages": tool_messages}

    def call_reply_model(state: AgentState, config: RunnableConfig) -> dict:
        """Writes the reply actually shown to the user - only present when split is True. The
        tool-model's own last ("no more tools needed") message stays in history for context, but
        is never itself shown; this node's output is the one run_turn surfaces."""
        response = reply_chat_model.invoke(_windowed_prompt(state), config=config)
        return {"messages": [response]}

    # Check if the last message has tool calls, if so route to the call_tools node; otherwise, end the turn.
    def route(state: AgentState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "call_tools"
        return "call_reply_model" if split else END

    graph = StateGraph(AgentState)
    graph.add_node("call_model", call_model)
    graph.add_node("call_tools", call_tools)
    graph.add_edge(START, "call_model")
    graph.add_conditional_edges("call_model", route)
    graph.add_edge("call_tools", "call_model")
    if split:
        graph.add_node("call_reply_model", call_reply_model)
        graph.add_edge("call_reply_model", END)
    return graph


def load_thread_messages(config: AgentCoreConfig, thread_id: str) -> list[Any]:
    """Return `thread_id`'s persisted messages, or `[]` if it has no checkpoint yet.

    Reads the raw checkpoint directly rather than building/compiling the full graph - replaying
    history into the chat UI on reconnect (Decisions Log Round 29) needs none of the tools, chat
    model, or collaborators `build_agent_graph` would otherwise construct.
    """
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.sqlite import SqliteSaver

    if not config.checkpoint_path.is_file():
        return []
    run_config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    with SqliteSaver.from_conn_string(str(config.checkpoint_path)) as checkpointer:
        checkpoint_tuple = checkpointer.get_tuple(run_config)
    if checkpoint_tuple is None:
        return []
    return checkpoint_tuple.checkpoint.get("channel_values", {}).get("messages", [])


def run_turn(
    config: AgentCoreConfig,
    vector_store: VectorStore,
    thread_id: str,
    user_text: str,
    memory_provider: MemoryProvider | None = None,
    pm_config: ProjectManagementConfig | None = None,
    web_search: WebSearch | None = None,
    chat_model: Any | None = None,
    reply_chat_model: Any | None = None,
    callbacks: list[Any] | None = None,
) -> TurnResult:
    """Run one user turn through Kathrena's agent graph, continuing `thread_id`'s prior history.

    If `memory_provider` is given, schedules (debounced) background memory extraction from the
    *full* conversation so far - not part of the graph itself, since memory formation happens
    outside Kathrena's live response turn (Decisions Log Round 8).

    `callbacks`, when given, are attached to the graph run's own config (Decisions Log Round 32)
    so e.g. Chainlit's `cl.LangchainCallbackHandler()` can turn the run's LLM/tool calls into
    visible UI steps.

    Note that the graph is rebuild from scratch on each turn, this is a simpler approach compared
    to maintaining a persistent graph instance across turns and allows for multiple concurrent
    conversations to be handled independently. The only caveat being that the SQLiteSaver will
    be blocked during concurrent access, causing delays in high traffic multi-user scenarios.
    """
    # Imported lazily so importing this module doesn't require langgraph-checkpoint-sqlite unless
    # a turn is actually run.
    from langchain_core.messages import HumanMessage
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.sqlite import SqliteSaver

    config.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(config.checkpoint_path)) as checkpointer:
        graph = build_agent_graph(
            config,
            vector_store,
            memory_provider=memory_provider,
            pm_config=pm_config,
            web_search=web_search,
            chat_model=chat_model,
            reply_chat_model=reply_chat_model,
        ).compile(checkpointer=checkpointer)
        run_config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        if callbacks:
            run_config["callbacks"] = callbacks
        last_ai_message = None
        for update in graph.stream(
            {"messages": [HumanMessage(content=user_text)]},
            config=run_config,
            stream_mode="updates",
        ):
            for node_output in update.values():
                messages = node_output.get("messages")
                if messages:
                    last_ai_message = messages[-1]

        if memory_provider is not None:
            # Create background memory extraction task (only runs if the conversation stays silent
            # for a bit to prevent excessive LLM usage)
            full_history = graph.get_state(run_config).values["messages"]
            memory_provider.remember(full_history, thread_id)

    reply = last_ai_message.text if last_ai_message is not None else ""
    return TurnResult(reply=reply)
