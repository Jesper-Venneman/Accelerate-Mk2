"""Chainlit chat app for Module K - run with `chainlit run src/kathrena/chat_interface/app.py -w`.

Design spec: Architecture/Modules/K - Chat Interface.md

Wires Chainlit's chat UI directly to Kathrena's agent graph (Module G) in-process - no separate
API server, per Architecture Overview.md#Runtime architecture.

Voice input: a `PushToTalkListener` (Module G) runs as a background task scoped to this Chainlit
session - starts in `on_chat_start`, stops in `on_chat_end`. Hold the configured hotkey to talk;
see Decisions Log Round 18. Voice output: turns that came in via that listener get a spoken
reply too (Kokoro + the voice-persona effects stage, Round 16); typed turns stay text-only.

Long-term memory: Kathrena's own memory (Module J) persists across restarts in a local database
and is recalled via her `search_memory` tool - see Decisions Log Round 19. This is separate from
reloading the actual chat transcript on restart, which isn't implemented (deferred by request).

Deadlines: Module I's on-demand `list_deadlines` skill - see Decisions Log Round 20. Web search:
an optional `search_web` tool backed by DuckDuckGo (no API key needed) - see Round 21. Both are
skills the LLM chooses to call, never run proactively on their own.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

import chainlit as cl
from chainlit.langchain.callbacks import DEFAULT_TO_IGNORE

from kathrena.agent_core.config import AgentCoreConfig
from kathrena.agent_core.graph import load_thread_messages, run_turn
from kathrena.agent_core.push_to_talk.config import PushToTalkConfig
from kathrena.agent_core.push_to_talk.listener import PushToTalkListener
from kathrena.agent_core.web_search import DuckDuckGoWebSearch, WebSearchConfig
from kathrena.chat_interface.audio import to_wav_bytes
from kathrena.chat_interface.config import VoiceOutputConfig
from kathrena.chat_interface.voice_effects import NullVoiceEffects, PedalboardVoiceEffects
from kathrena.config import PipelineConfig
from kathrena.memory import LangMemProvider, MemoryConfig, open_memory_store
from kathrena.project_management import ProjectManagementConfig
from kathrena.rag_index.config import RagIndexConfig
from kathrena.rag_index.vector_store import ChromaVectorStore
from kathrena.settings import SettingsNotConfiguredError, ensure_configured, get_store
from kathrena.voice_log.transcription import WhisperTranscriber

try:
    ensure_configured()
except SettingsNotConfiguredError as exc:
    raise SystemExit(str(exc)) from exc

# Chainlit's own logging setup leaves these at INFO, which floods startup with routine HTTP/model
# housekeeping noise from embeddings/HF Hub lookups - not useful day-to-day.
# ALWAYS CHECK LOG LEVELS WHEN DEBUGGING.
for _noisy_logger in ("httpx", "sentence_transformers", "huggingface_hub"):
    logging.getLogger(_noisy_logger).setLevel(logging.WARNING)

# Build module-level singletons for the agent, tools, and configurations:
## Agent Core
_agent_config = AgentCoreConfig()

## Vector Store
_vector_store = ChromaVectorStore(RagIndexConfig())

## Memory Store
_memory_config = MemoryConfig()
_memory_provider = LangMemProvider(_memory_config, open_memory_store(_memory_config))

## Project Management
_pm_config = ProjectManagementConfig()

## Web Search
_web_search_config = WebSearchConfig()
_web_search = DuckDuckGoWebSearch() if _web_search_config.enabled else None

## Push-to-Talk
_push_to_talk_config = PushToTalkConfig()
# Reuses Module B's transcriber/config - a second, independent Whisper instance in this process,
# separate from the voice-log pipeline's own (which runs as its own process).
_push_to_talk_transcriber = WhisperTranscriber(PipelineConfig())

## Voice Output
_voice_output_config = VoiceOutputConfig()
_tts = None
_voice_effects = NullVoiceEffects()
if _voice_output_config.enabled:
    from kathrena.chat_interface.tts import KokoroTextToSpeech

    _tts = KokoroTextToSpeech(_voice_output_config)
    _voice_effects = PedalboardVoiceEffects(_voice_output_config)


_THREAD_ID_KEY = "thread_id"
_LISTENER_KEY = "push_to_talk_listener"
_LISTENER_TASK_KEY = "push_to_talk_task"

# Names of LangGraph's own internal per-node "chain" runs (Module G's graph.py node names, plus
# its conditional-edge router and the graph itself) - without this, Chainlit's tracer renders each
# one as its own "thinking" step showing the raw AgentState dict (messages) as
# input, which is redundant noise next to the already-clean nested tool/llm steps. Verified by
# probing run_turn with a plain callback handler logging on_chain_start's run name/type.
_CHAIN_STEPS_TO_IGNORE = [*DEFAULT_TO_IGNORE, 
                          "LangGraph", 
                          "call_model", 
                          "call_reply_model", 
                          "call_tools", 
                          "route"]

# Thread ids currently bound to an open Chainlit session (Decisions Log Round 29) - a restart
# resumes whichever thread was last active, but a *second* concurrent tab never resumes the same
# one out from under it; it just gets its own fresh thread, same as before this round.
_active_thread_ids: set[str] = set()


async def _handle_turn(user_text: str, thread_id: str, *, speak: bool) -> None:
    """Run one turn through Kathrena's agent and show the result.

    Shared by typed messages and push-to-talk ones - only the latter (`speak=True`) also gets
    synthesized and played back. A fresh `cl.LangchainCallbackHandler()` per turn turns the 
    run's LLM/tool calls into visible nested steps.
    """
    async with cl.Step(name="thinking"):
        result = await cl.make_async(run_turn)(
            AgentCoreConfig(),  # fetched fresh each turn so e.g. tool_profiles are hot-swappable
            _vector_store,
            thread_id,
            user_text,
            memory_provider=_memory_provider,
            pm_config=_pm_config,
            web_search=_web_search,
            callbacks=[cl.LangchainCallbackHandler(to_ignore=_CHAIN_STEPS_TO_IGNORE)],
        )

    # Synthesize and play back the response verbally if needed.
    elements = []
    if (speak or _voice_output_config.always_speak) and _tts is not None:
        clip = await cl.make_async(_tts.synthesize)(result.reply)
        clip = await cl.make_async(_voice_effects.apply)(clip)
        elements = [cl.Audio(name="kathrena-reply.wav", content=to_wav_bytes(clip), auto_play=True)]
    await cl.Message(content=result.reply, elements=elements).send()


async def _consume_push_to_talk_utterances(listener: PushToTalkListener, thread_id: str) -> None:
    """Forward each push-to-talk utterance into this session's conversation."""
    while True:
        text = await listener.utterances.get()
        # type="user_message" is what puts it on the right - cl.Message defaults to
        # "assistant_message" otherwise, regardless of author.
        await cl.Message(content=text, author="You (voice)", type="user_message").send()
        await _handle_turn(text, thread_id, speak=True)


async def _replay_history(messages: list) -> None:
    """Re-render a resumed thread's past turns (Decisions Log Round 29).

    Only what the user actually typed/said and what Kathrena actually replied get shown again -
    tool calls and tool outputs are internal plumbing, never shown live either. Known rough edge:
    in a "split" tool/reply-profile conversation (Further Considerations), the tool-model's own
    discarded draft also carries content and would replay as an extra line - rare enough not to
    special-case yet.
    """
    from langchain_core.messages import AIMessage, HumanMessage

    for message in messages:
        if isinstance(message, HumanMessage) and message.content:
            # type="user_message" is what puts it on the right - Chainlit renders side from this,
            # not from author (cl.Message defaults to "assistant_message" otherwise).
            await cl.Message(content=message.text, author="You", type="user_message").send()
        elif isinstance(message, AIMessage) and message.content:
            await cl.Message(content=message.text).send()


@cl.on_chat_start
async def on_chat_start() -> None:
    # Resume the last active thread across a restart if nothing else already claimed it this
    # run (Decisions Log Round 29) - a second concurrent tab still gets its own fresh thread,
    # same isolation as before this round.
    store = get_store()
    last_thread_id = store.value("agent_core", "last_thread_id", "")
    history: list = []
    if last_thread_id and last_thread_id not in _active_thread_ids:
        thread_id = last_thread_id
        history = await cl.make_async(load_thread_messages)(_agent_config, thread_id)
    else:
        thread_id = str(uuid.uuid4())
    _active_thread_ids.add(thread_id)
    store.set_value("agent_core", "last_thread_id", thread_id)
    cl.user_session.set(_THREAD_ID_KEY, thread_id)

    if history:
        await _replay_history(history)
    else:
        await cl.Message(
            content=(
                f"Hi, I'm {_agent_config.agent_name}. Ask me about your projects, ask me to update a note, "
                f"or hold {_push_to_talk_config.hotkey_name} to talk to me."
            )
        ).send()

    # Scoped to this session - starts when the tab opens, stops when it closes. Runs on its own
    # background thread/OS keyboard hook; see PushToTalkListener for why.
    # Guards against on_chat_start somehow firing twice for the same session (observed with
    # Chainlit's -w reload) - never leave two listeners/keyboard hooks running at once.
    _stop_existing_push_to_talk_listener()
    listener = PushToTalkListener(_push_to_talk_config, _push_to_talk_transcriber)
    listener.start(asyncio.get_running_loop())
    cl.user_session.set(_LISTENER_KEY, listener)
    task = asyncio.create_task(_consume_push_to_talk_utterances(listener, thread_id))
    cl.user_session.set(_LISTENER_TASK_KEY, task)


def _stop_existing_push_to_talk_listener() -> None:
    listener: PushToTalkListener | None = cl.user_session.get(_LISTENER_KEY)
    if listener is not None:
        listener.stop()
    task: asyncio.Task | None = cl.user_session.get(_LISTENER_TASK_KEY)
    if task is not None:
        task.cancel()


@cl.on_chat_end
async def on_chat_end() -> None:
    _stop_existing_push_to_talk_listener()
    thread_id: str | None = cl.user_session.get(_THREAD_ID_KEY)
    if thread_id is not None:
        _active_thread_ids.discard(thread_id)


@cl.on_message
async def on_message(message: cl.Message) -> None:
    thread_id = cl.user_session.get(_THREAD_ID_KEY)
    await _handle_turn(message.content, thread_id, speak=False)
