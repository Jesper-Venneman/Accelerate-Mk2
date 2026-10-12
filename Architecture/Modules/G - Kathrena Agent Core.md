The conversational AI companion, named **Kathrena** - an ongoing companion project with an interface that's evolved for years. This is the first time she gets an actual LLM-backed "brain" behind that interface.

## Responsibilities
- Reachable by push-to-talk (hold a hotkey while a [K - Chat Interface](K%20-%20Chat%20Interface.md) session is open) or by typing directly into [K - Chat Interface](K%20-%20Chat%20Interface.md).
- Retrieves context from [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md) and [J - Memory Module](J%20-%20Memory%20Module.md), generates responses via chat models resolved from named `llm_profiles` entries (`kathrena.llm`, Decisions Log Round 27) - independent from [E - Refinement and Summarization Module](E%20-%20Refinement%20and%20Summarization%20Module.md) and [J - Memory Module](J%20-%20Memory%20Module.md)'s own profile choice, though all can point at the same "local" profile by default.
- Also has on-demand tools for deadlines ([I - Project Management Modules](I%20-%20Project%20Management%20Modules.md)'s I3, `list_deadlines`), web search (`search_web`), reading a vault note's full contents (`read_vault_file`), switching LLM modes (`set_llm_mode`) and individual settings (`change_setting`), and the current date/time (`get_current_datetime`) - see their sections below.
- Screen perception ([L - Screen Perception Module](L%20-%20Screen%20Perception%20Module.md)) is planned but not built - design only, see Decisions Log Round 22.
- Both proactive (briefings, suggestions) and reactive (answers on request), configurable.
- The personality/behaviour system prompt (`agent_core.system_prompt`) is editable in `data/settings.yaml` without touching code (Decisions Log Round 31) - only the sentence describing the always-available tools stays hardcoded in `kathrena.agent_core.graph`, so it can't drift out of sync with which tools actually exist.
- Any change she wants to make to the vault goes through [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md) - never a direct write. **Currently disabled** (the `propose_vault_change` tool is commented out) pending a rework - see Further Considerations' "Disconnect the Approval Gate" note.
- Orchestrated as a LangGraph agent (a graph of tool-calling nodes), the same framework backing [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md) and [I - Project Management Modules](I%20-%20Project%20Management%20Modules.md).
- Push-to-talk is a separate microphone-capture flow from [A - Ingestion and Sync Layer](A%20-%20Ingestion%20and%20Sync%20Layer.md)'s voice-log recording - different purposes, run independently.

## Push-to-talk voice input
A wake-word listener (continuous energy-gated Whisper scanning) was tried first and abandoned - unstable and resource-heavy in practice (constant transcription, false triggers). See Decisions Log Round 18.

Instead: a global keyboard hook (via `pynput`) watches one configurable key, system-wide and regardless of which window has focus, without suppressing the key's normal behavior elsewhere - it only observes, never swallows the keypress. Holding it starts recording; releasing it stops, transcribes via [B - Transcription Module](B%20-%20Transcription%20Module.md)'s Whisper transcriber, and sends the question - unless the transcript is empty, which just means an accidental tap or a normal press of that key elsewhere, not a real question.

Listening is scoped to an open [K - Chat Interface](K%20-%20Chat%20Interface.md) session (starts when the chat tab opens, stops when it closes) rather than a fully independent, browser-independent service - the latter would need its own delivery mechanism (auth, sockets, session discovery) for pushing a message into Chainlit from outside its own process, a lot of extra moving parts for a single-user local app.

**Platform note:** works on Windows and Linux/X11 sessions. Native Wayland sessions restrict global input listening for security reasons (a deliberate compositor design choice, not specific to this project) - Xwayland-compatible apps still work, but a pure-Wayland desktop may not receive the hotkey reliably.

## Web search
A `search_web` tool for questions about anything current or outside the vault/memory, backed by DuckDuckGo (via the `ddgs` package - no API key or account needed, see Decisions Log Round 21). Lives in `kathrena.agent_core.web_search`, behind a `WebSearch` Protocol so the backend can be swapped later without touching the tool-calling loop - the same pattern as [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md)'s `VectorStore` and [J - Memory Module](J%20-%20Memory%20Module.md)'s `MemoryProvider`. Optional: `None` means no tool at all, controlled by `WEB_SEARCH_ENABLED`.

## Current date/time
A `get_current_datetime` tool - Kathrena (and the LLM itself) otherwise has no sense of "now". Always available, unlike the tools above, since it needs no optional collaborator to work.

## LLM modes and settings (Decisions Log Round 28)
Two profile fields, not one: `tool_profile` (decides which tool(s) to call) and `reply_profile` (writes the reply actually shown) - split specifically so "standard mode" below can use a cheap local model for tool-calling and a stronger cloud model only for the final answer. When the two are equal (the default, and `local`/`cloud` modes), the agent graph behaves exactly as it always has - one model, one node, no added cost; only when they differ does a second `call_reply_model` node get added, running once after the tool-calling loop stops requesting tools.

- **`set_llm_mode(mode)`** - a fixed macro over three named combinations, not a stored setting:
  - `local` - every role (Module E/G/J) on the local profile.
  - `cloud` - every role on the cloud profile.
  - `standard` - Module G's `reply_profile` on cloud, everything else (Module E/J, and G's own `tool_profile`) stays local - spends cloud only on the part actually shown to the user.
- **`change_setting(name, value)`** - more generic, allow-listed individual settings including `pipeline.llm_profile`, `agent_core.tool_profile`, `agent_core.reply_profile`, and `memory.llm_profile` - lets a single role's profile change without applying a whole mode. Secrets/paths/`vault_root` are never on this allow-list (vault content Kathrena reads via her own tools is untrusted input reaching this same model - an indirect prompt-injection concern, not just a style choice).
- **Scope of "freeing the GPU"**: switching to `cloud`/`standard` only stops Kathrena's own new requests to local TextGen - it does not unload TextGen's model from VRAM, stop the TextGen process, or affect RAG/memory embeddings, Whisper, or Kokoro, all of which stay local regardless of mode.

## Bounded conversation context (Decisions Log Round 30)
The checkpointed thread history (`state["messages"]`) is append-only and keeps growing for as long as a thread lives - now potentially across restarts too, since [K - Chat Interface](K%20-%20Chat%20Interface.md) resumes the last thread (Round 29). `call_model`/`call_reply_model` never send that whole accumulated history to the LLM: a shared `_windowed_prompt` helper trims it to the last `agent_core.history_window_messages` messages (default `12`, a message count not a token budget) via `langchain_core.messages.trim_messages`, always starting the window on a `HumanMessage` boundary so a tool-calling exchange never gets cut mid-way. Only the live prompt is capped - the checkpointed state itself, and anything reading it (like [J - Memory Module](J%20-%20Memory%20Module.md)'s extraction), still sees the full history. See [Memory Context Management](../Investigations/Memory%20Context%20Management.md).

## Generation token cap (Decisions Log Round 31)
Separate from the context-window cap above: `kathrena.llm.LLMProfile.max_tokens` bounds how much a *single reply* is allowed to generate, passed straight through to `init_chat_model`. Applies per named profile, so it covers every role (Module E/G/J) through the one centralized `build_chat_model`, not just Module G. `cloud` seeds with a `8192` default (cloud generation costs real money per token - prompted by an actual incident of an unhelpfully long, costly cloud reply); `local` stays uncapped by default. Editable per profile in `data/settings.yaml`'s `llm_profiles.<name>.max_tokens`.

## Revealed thinking and tool-call/LLM-call logging (Decisions Log Round 32)
[K - Chat Interface](K%20-%20Chat%20Interface.md) attaches a fresh `cl.LangchainCallbackHandler()` to each turn's graph run, which turns LLM calls into visible nested UI steps automatically. Tool calls needed more: `call_tools` used to call plain Python functions directly, bypassing LangChain's callback system entirely - tools are now wrapped with `langchain_core.tools.tool()` where `build_agent_graph` collects them (not inside `agent_core.tools.py`'s own factories) and invoked via `.invoke(args, config=config)`, with an explicit `config: RunnableConfig` threaded through `call_model`/`call_tools`/`call_reply_model`, so tool calls nest correctly as their own visible steps too.

Separately, `kathrena.llm_logging` gives a shared plain-text call log (`data/logs/llm_calls.log`, rotated daily, last 10 days kept).

## Related
- [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md)
- [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md)
- [I - Project Management Modules](I%20-%20Project%20Management%20Modules.md)
- [J - Memory Module](J%20-%20Memory%20Module.md) - her long-term memory of conversations and people, kept separate from vault RAG
- [K - Chat Interface](K%20-%20Chat%20Interface.md) - the actual UI surface for talking to her
- [L - Screen Perception Module](L%20-%20Screen%20Perception%20Module.md) - planned visual sense of the active window, not built yet
