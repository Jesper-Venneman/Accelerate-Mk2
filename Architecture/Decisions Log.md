Chronological record of major calls made during design, so we don't relitigate them without reason.

## Round 1
- **R AI B project:** ignored - Mk2 is standalone, not a stepping stone toward the older "R AI B" brain-architecture sketch.
- **Interaction surface:** combination - voice logging keeps working like Mk1; [Kathrena](Modules/G%20-%20Kathrena%20Agent%20Core.md) is a separate conversational layer reachable by voice or chat.
- **LLM backend:** hybrid - local by default, cloud optional per task.
- **RAG scope:** entire vault, but configurable per-project (opt-out).
- **Hardware device:** not built now; see [A - Ingestion and Sync Layer](Modules/A%20-%20Ingestion%20and%20Sync%20Layer.md) for why the design doesn't need to special-case it.
- **Project management:** all five sub-features wanted, but as separate modules - see [I - Project Management Modules](Modules/I%20-%20Project%20Management%20Modules.md). (Task tracking later cut from scope, see Round 6.)
- **Transcription:** open to upgrading from plain Whisper (e.g. faster-whisper).
- **Personality/behaviour:** both proactive and reactive, configurable.

## Round 2
- **Kathrena's write access:** always proposes changes; user approves before anything touches the vault - see [H - Change Proposal and Approval Gate](Modules/H%20-%20Change%20Proposal%20and%20Approval%20Gate.md).
- **Voice-log pipeline:** rewrite as a new modular system, reusing Mk1's proven logic (synonym map, whisper, log format) rather than keeping `VoiceLog_Processor.py` running as-is.
- **Deployment scope:** this desktop only; recording-from-anywhere is solved by existing external sync (out of scope here) landing files into a watched folder.
- **Kathrena's voice trigger:** wake-word, always-listening.

## Round 3
- **Orchestration framework:** LangGraph, shared across [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md), [H - Change Proposal and Approval Gate](Modules/H%20-%20Change%20Proposal%20and%20Approval%20Gate.md), and [I - Project Management Modules](Modules/I%20-%20Project%20Management%20Modules.md). Uses `interrupt()` + `Command(resume=...)` to pause on proposed changes, with the built-in `SqliteSaver` checkpointer for durable persistence across restarts and long delays before you get around to reviewing. Chosen over LlamaIndex Workflows (better fit if RAG also ends up on LlamaIndex, but no built-in checkpointer), AutoGen/Semantic Kernel (weaker async/delayed-approval story), and a hand-rolled proposal queue (more to build ourselves).

## Round 4
- **Approval-gate review UI:** chat window for v1 - proposals surface as approve/reject/edit prompts in the same conversation you already have with Kathrena, no extra UI or API to build. A dedicated Obsidian plugin (custom `ItemView` panel, backed by a small local HTTP API from the Python service) is a planned phase-2 enhancement, not initial scope.
- **RAG implementation stack:** LangChain's components (text splitters, embeddings interface, vector store integrations) for the actual chunk/embed/upsert/retrieve plumbing - LangGraph itself has no built-in RAG tooling, it's purely an orchestration layer. LangGraph still orchestrates the indexing run for the checkpointed/resumable benefit. See [F - RAG Indexing Module](Modules/F%20-%20RAG%20Indexing%20Module.md).

## Round 5
- **No paid options, anywhere:** every remaining tech-stack pick must be free to self-host/run locally, no accounts, API keys, or usage tiers that could later hit a paid wall.
- **Vector store:** Chroma - embedded (no server process), Apache-2.0, best-documented LangChain integration. Free either way since it's self-hosted, but simplest operationally.
- **Embedding model:** BAAI/bge-small-en-v1.5 - MIT licensed, ~130MB, runs locally via `sentence-transformers`, strong quality-for-size, independent of whichever local LLM runtime gets picked later.
- **Wake-word engine:** openWakeWord over Porcupine - Apache-2.0, `pip install openwakeword`, runs fully locally with no account/API key/usage limits. Porcupine's free tier is a free tier *of a commercial product* (Picovoice account/AccessKey, paid tiers beyond free limits) - explicitly avoided per the no-paid-options rule.
- **Fallback candidates kept on file:** LanceDB/Qdrant (vector store) and nomic-embed-text/all-MiniLM-L6-v2 (embedding model), documented in [F - RAG Indexing Module](Modules/F%20-%20RAG%20Indexing%20Module.md) in case we need to pivot away from Chroma/bge-small-en-v1.5.

## Round 6
- **Per-project RAG opt-out:** confirmed - a frontmatter flag next to `synonyms:`, e.g. `rag-index: false`. Not critical, but cheap to implement, so worth doing. See [F - RAG Indexing Module](Modules/F%20-%20RAG%20Indexing%20Module.md).
- **Task/checklist tracking (I1) cut from scope:** deferred, not part of the initial build. Bidirectional sync against manual checkbox edits needs a proper design before it's worth building - revisit as its own design pass later rather than reusing the current stub. Project management now ships with four modules (I2-I5) instead of five. See [I - Project Management Modules](Modules/I%20-%20Project%20Management%20Modules.md).

## Round 7
- **Kathrena's personality:** warm and casual tone; relationship is a mix - task-focused for logs/PM work, more companion-like in open conversation; diplomatic when she disagrees (raises concerns gently, ultimately defers); humor comes through occasionally rather than constantly. Defined fresh rather than pulled from prior versions of Kathrena - this is her first LLM-backed "brain". See [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md).
- **3D rig avatar interface:** future phase, not part of Mk2 - same treatment as the ESP32 hardware device. [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md) stays interface-agnostic (plain text/audio responses) so an avatar/animation layer can plug in later without a redesign.

## Round 8
- **Kathrena's long-term memory:** a background memory-formation agent (not Kathrena's live response turn) extracts and categorizes memories from conversations, written to a dedicated store kept separate from the Obsidian vault, indexed for its own semantic search. See [J - Memory Module](Modules/J%20-%20Memory%20Module.md).
- **Memory tooling:** LangMem (MIT, LangChain team) - a purpose-built background memory manager plus hot-path tools, on top of LangGraph's native long-term memory `Store`, the same orchestration family already used everywhere else. Backing vector store reuses Chroma (a separate collection from the vault index) rather than standing up Postgres just for memory.
- **Rejected: Mem0** - Apache-2.0 core, but defaults point at paid OpenAI APIs and its self-hosted tier withholds advanced features for the paid cloud platform - weaker fit for the no-paid-options rule than LangMem.

## Round 9
- **Memory categorization:** adopt LangMem's own framework instead of a custom taxonomy - Profile (single evolving doc) for the user's own facts/preferences, Collection for other people/general facts, Episodic for past-conversation summaries. See [J - Memory Module](Modules/J%20-%20Memory%20Module.md).
- **Memory formation trigger:** LangMem's `ReflectionExecutor` debounced background processing - waits until a conversation goes idle before extracting memories, instead of after every message or a rigid schedule.
- **Memory retention:** rely on LangMem's built-in consolidation (updates/removes outdated memories automatically) plus importance/recency-weighted retrieval ranking - no separate hard cap/expiry policy for now.

## Round 10
- **Local LLM runtime:** oobabooga's TextGen (formerly text-generation-webui) - already in use, free/AGPL-3.0, 100% offline/private/no telemetry, exposes an OpenAI/Anthropic-compatible API with tool-calling support (needed for LangGraph agent nodes), supports multiple backends (llama.cpp, ExLlamaV3, Transformers, TensorRT-LLM) and switching models without restarting.
- **Cloud model connector:** LangChain's `init_chat_model()` plus the relevant provider package (`langchain-openai`, `langchain-anthropic`, etc.) - a single universal abstraction already part of our stack, so switching between local (via a `base_url` override pointed at TextGen) and cloud is just a config change, no separate connector library needed.
- **Specific model:** deliberately left unpinned - swapping models in TextGen doesn't require a restart, and cloud provider/model choice is just a string passed to `init_chat_model()`. See [E - Refinement and Summarization Module](Modules/E%20-%20Refinement%20and%20Summarization%20Module.md).

## Round 11
- **Transcription engine:** faster-whisper (MIT, CTranslate2-based) - up to 4x faster than plain `openai-whisper` with less memory, same accuracy, int8 quantization for CPU. See [B - Transcription Module](Modules/B%20-%20Transcription%20Module.md).
- **I2-I5 implementation pattern:** split into skills (bound tools Kathrena calls directly, single-shot) vs. sub-agents (own LangGraph subgraph, autonomous/background, like [J - Memory Module](Modules/J%20-%20Memory%20Module.md)). I2 (dashboard) and I5 (search/query) are skills; I3 (deadlines/reminders) and I4 (auto note updater) are sub-agents, since both need multi-step reasoning or background/proactive execution. See [I - Project Management Modules](Modules/I%20-%20Project%20Management%20Modules.md).

## Round 12
- **Build sequencing:** ship and evaluate the core RAG + Kathrena agent first ([F - RAG Indexing Module](Modules/F%20-%20RAG%20Indexing%20Module.md), [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md), and what they depend on) before speccing I2-I5's deeper details (tool signatures, I3's scheduling, etc.). Real usage should inform the remaining project-management features better than speccing them blind now.

## Round 13
- **Chat interface:** Chainlit (Apache-2.0, pure Python, self-hosted, free) - see [K - Chat Interface](Modules/K%20-%20Chat%20Interface.md) (new module). Chosen over LangChain's official Agent Chat UI (MIT, purpose-built for LangGraph, but a separate Next.js/TypeScript app requiring its own self-hosted LangGraph API server, and approve/reject would need custom "Artifact" component work rather than being a built-in widget). Chainlit's `cl.Action` buttons map directly onto [H - Change Proposal and Approval Gate](Modules/H%20-%20Change%20Proposal%20and%20Approval%20Gate.md)'s approve/reject/edit flow, and it stays pure Python - no second language ecosystem for a single-user project.

## Round 14
- **Wake-word vs voice-log recording:** confirmed separate flows - [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md)'s always-on wake-word listener and [A - Ingestion and Sync Layer](Modules/A%20-%20Ingestion%20and%20Sync%20Layer.md)'s voice-log recording are independent microphone-capture paths for different purposes.
- **Runtime architecture:** one long-running Python process embeds LangGraph directly in-process (compiled graphs called via `.invoke()`/`.stream()`) rather than using `langgraph dev`/the LangGraph API server/Studio - that tooling nudges toward a LangSmith account and is oriented at their production deployment offering, which conflicts with the no-paid/no-account rule (Round 5) even though sign-up is nominally free. A shared `SqliteSaver` checkpointer and a shared LangGraph `Store` (both local SQLite files) persist [H - Change Proposal and Approval Gate](Modules/H%20-%20Change%20Proposal%20and%20Approval%20Gate.md) and [J - Memory Module](Modules/J%20-%20Memory%20Module.md) state across restarts with no external service. The voice-log pipeline (A-E) and [F - RAG Indexing Module](Modules/F%20-%20RAG%20Indexing%20Module.md)'s watcher run as separate background tasks, independent of the live chat agent. See [Architecture Overview](Architecture%20Overview.md).

## Round 15
- **Transcription engine, reversed:** back to plain **openai-whisper**, replacing faster-whisper from Round 11. During the first real smoke test, faster-whisper's CTranslate2 GPU backend failed (missing CUDA 12 cuBLAS runtime); installing the `nvidia-cublas-cu12`/`nvidia-cudnn-cu12` packages it needs still didn't fix it. The user has hit reliability issues with faster-whisper before this project too. openai-whisper is the package Mk1 already used successfully, and (unlike faster-whisper) depends on `torch`, whose CUDA build we already confirmed works on this machine (`torch-2.13.0+cu130`, RTX 5090 detected) - so this is a reversion to known-working behavior, not a new risk. Requires `ffmpeg` on PATH (confirmed present). See [B - Transcription Module](Modules/B%20-%20Transcription%20Module.md).

## Round 16
- **Kathrena's text-to-speech engine:** Kokoro-82M (Apache-2.0) - small/fast enough for CPU, better voice quality than the lighter alternatives. Piper (MIT) and pyttsx3 (OS-native SAPI voices) kept on file as fallback candidates if Kokoro proves too heavy or a poor match for the voice-persona effects stage. See [K - Chat Interface](Modules/K%20-%20Chat%20Interface.md).
- **When Kathrena speaks:** only for turns that came in through the wake-word voice path - a typed question gets a typed answer, since you're already at the screen. No separate push-to-talk mic button in the Chainlit window itself; the wake-word listener ([G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md)) stays the only voice-input path, feeding transcribed text into the same chat session as if typed. See [K - Chat Interface](Modules/K%20-%20Chat%20Interface.md).
- **Kathrena's voice persona:** a separate, swappable DSP-only voice-effects stage (pitch/formant shift, EQ/timbre) reshapes Kokoro's generic output toward Kathrena's established voice from her earlier, non-public, pre-AI TTS system - an approximate match via signal processing, not trained voice cloning/conversion (e.g. RVC, OpenVoice), which is a possible future upgrade if the DSP approximation isn't convincing enough. Reference audio clips exist in the Kathrena 1.0 source project but aren't stored in this repo. See [K - Chat Interface](Modules/K%20-%20Chat%20Interface.md).

## Round 17
- **Wake-word engine, reversed:** dropped openWakeWord (Round 5), replaced with continuous energy-gated Whisper scanning. openWakeWord only ships pretrained models for a handful of fixed phrases (alexa, hey mycroft, hey jarvis, etc.) - none of them "Kathrena" - and training a custom model is a separate, substantial undertaking (synthetic TTS training data, hours of negative audio, a full training run), not something to fold into this pass. Instead, a cheap RMS-energy check gates whether a rolling audio chunk is worth transcribing at all, and [B - Transcription Module](Modules/B%20-%20Transcription%20Module.md)'s existing Whisper transcriber does the actual listening - scanning short chunks for the name while idle, then transcribing the full follow-up question once triggered. Heavier than a dedicated wake-word model at idle, but this machine's GPU already proved fast enough for Whisper (Round 15), and it directly supports the literal word "Kathrena" without an ML training investment. `openwakeword` removed from `pyproject.toml`; `sounddevice` added for microphone capture. See [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md).
- **Wake-word listening scope:** tied to an open [K - Chat Interface](Modules/K%20-%20Chat%20Interface.md) (Chainlit) session - starts when the chat tab opens, stops when it closes - rather than a fully independent, browser-independent background service. The latter would need its own delivery mechanism (auth, sockets, session discovery) to push a message into Chainlit from outside its own process; a lot of extra moving parts for a single-user local app, versus simply starting the listener as a background task scoped to the session in `on_chat_start`. See [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md).

## Round 18
- **Wake-word listening, abandoned:** the Round 17 continuous energy-gated Whisper scanning approach turned out unstable and resource-heavy in real use (the constant background Whisper calls were flaky and wasteful, not just theoretically heavier). Replaced with **push-to-talk**: hold a key, speak, release. No continuous transcription, no phrase matching, no false triggers - the mic and Whisper are only touched for the exact duration of an actual question.
- **Push-to-talk hotkey library:** `pynput` (LGPLv3) - cross-platform (Windows, Linux/X11, macOS), and critically its `Listener` is passive by default (`suppress=False`): it only observes key events, it never blocks them from reaching the rest of the system, satisfying the requirement that the hotkey still work normally everywhere else. A global low-level hook, so it fires regardless of which window has focus - no extra work needed for "system-wide."
- **Push-to-talk platform limits (accepted):** on Linux, `pynput` needs an X server (works fine in a normal X11 desktop session, no root required) or falls back to `uinput` (needs root). Under native Wayland, global input listening is restricted for security reasons by the compositor itself - a limitation of the platform, not of this library or any alternative. Documented rather than worked around; Xwayland-compatible apps are unaffected.
- **Default hotkey:** Scroll Lock - present on most keyboards, essentially unused by modern software, configurable via `PTT_HOTKEY` to any `pynput.keyboard.Key` name for keyboards without it. See [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md).
- **Transcription blocking hazard, fixed:** pynput's own docs warn that long-running/blocking calls inside its listener callbacks risk freezing keyboard/mouse input system-wide. Whisper transcription is therefore dispatched to a plain background thread on key-release, never run directly on pynput's callback thread. See [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md).

## Round 19
- **Memory backing store: `SqliteStore`, not Chroma:** Round 9's plan to reuse Chroma for [J - Memory Module](Modules/J%20-%20Memory%20Module.md) is superseded - `langgraph.store.sqlite.SqliteStore` (bundled inside the already-installed `langgraph-checkpoint-sqlite` package, zero new dependencies) is a persistent, file-based `BaseStore` with built-in vector search via `sqlite-vec`, confirmed installed and working via a direct put/search smoke test. It needed no custom adapter code, unlike a hand-built Chroma-backed `BaseStore`. Lives in its own file (`data/memory.sqlite`), kept open for the process's lifetime since it's internally thread-safe.
- **Memory taxonomy, simplified for now:** rather than building Round 9's full Profile/Collection/Episodic taxonomy up front, [J - Memory Module](Modules/J%20-%20Memory%20Module.md) ships with unstructured/schema-less memories in a single fixed namespace (`("memories", "kathrena")`) for this pass, deferring the fuller categorization to a later pass once the simpler version is proven out in real use.
- **Memory formation debounce, full history required:** LangMem's `ReflectionExecutor` cancels/reschedules per `thread_id`, so only the *last* submission before a conversation goes idle actually runs. [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md)'s `run_turn` therefore submits the *full* accumulated conversation history (via the checkpointer's state) on every turn, not just the latest exchange, so the eventual single extraction run still sees the whole conversation.
- **Chat transcript reload on restart, deferred:** reloading the actual visible conversation history in [K - Chat Interface](Modules/K%20-%20Chat%20Interface.md) across app restarts is explicitly out of scope for this pass - a separate feature from Kathrena's own semantic memory (this module), which persists and is recalled regardless. Revisit later if wanted.

## Round 20
- **I3 (deadlines/reminders) built as an on-demand skill, not a background sub-agent:** the split in [I - Project Management Modules](Modules/I%20-%20Project%20Management%20Modules.md) originally called for I3 to run proactively in the background. Simplified instead to a `list_deadlines` tool Kathrena only calls when asked (e.g. "are there any close deadlines?") - she doesn't surface due dates unprompted. Revisit proactive delivery later if the on-demand form proves useful but insufficient.
- **Due dates via a flat `due:` frontmatter field:** any vault note can carry `due: 2026-09-15` to be picked up by `list_deadlines` - no new task-tracking data model, consistent with I1 (checklist tracking) staying cut from scope (Round 6). Overdue notes are always included in results, not silently dropped, since they're arguably the closest deadlines of all.

## Round 21
- **Web search added as a Module G tool, not a new lettered module:** gives Kathrena a `search_web` tool for up-to-date information outside the vault/memory. Implemented as `kathrena.agent_core.web_search` - a subpackage of Module G, the same relationship push-to-talk already has to G - rather than a new top-level lettered module, since it's a single bound tool, not an independent subsystem.
- **Web search backend: DuckDuckGo via the `ddgs` package**, not `langchain_community`'s `DuckDuckGoSearchAPIWrapper` - that wrapper is a thin shim over the same `ddgs` package and pulls in `langchain-community` (which is being sunset upstream) plus several unrelated transitive dependencies (SQLAlchemy, `langchain-classic`) for no benefit here. Calling `ddgs` directly, behind this project's own `WebSearch` Protocol (matching `VectorStore`/`MemoryProvider`'s swappable pattern), keeps the dependency footprint minimal and the door open to swap in Tavily or another provider later if DuckDuckGo's result quality or rate limits become a problem. DuckDuckGo needs no API key or account, matching the project's free/local-by-default preference (Round 1).
- **`search_web` gated behind an explicit `web_search` param**, same shape as `memory_provider`/`pm_config` - `None` (the default) means no tool at all, so every existing caller/test is unaffected. Whether it's constructed at all is controlled by `WEB_SEARCH_ENABLED` (`kathrena.agent_core.web_search.WebSearchConfig`); how many hits it asks for per call is `AgentCoreConfig.web_search_max_results`, alongside `rag_top_k` - both are "how many results per tool call" knobs owned by Module G itself.
- **`get_current_datetime` added as an always-available tool:** Kathrena otherwise has no sense of "now" at all (the LLM itself has no clock), which the deadlines tool also needs internally (its own due-date/today math, done directly in `kathrena.project_management.deadlines`, doesn't call this tool - the two are independently useful, not coupled). Unlike the other new tools, this needs no optional collaborator, so it's unconditionally present rather than gated behind a `None`-checked parameter.

## Round 22
- **Screen perception designed as a new lettered module ([L - Screen Perception Module](Modules/L%20-%20Screen%20Perception%20Module.md)), not a Module G subpackage:** unlike web search (Round 21), this capability's scope includes a background proactive loop, not just a bound tool - the same on-demand-tool-plus-independent-background-process shape as [J - Memory Module](Modules/J%20-%20Memory%20Module.md), not push-to-talk/web search's simpler "single bound tool" shape. **Design only for this round - not built.** Deferred until the open questions below are verified hands-on (explicitly: it's late, can't test the TextGen side right now).
- **Scope: both the on-demand tool and the proactive/periodic stretch goal are in scope for the eventual build**, not staged as separate later phases - unlike I3 (Round 20), which shipped as skill-only with proactive delivery explicitly deferred. Continuous/real-time vision or reacting to every frame is explicitly ruled out regardless - the proactive loop must poll rarely (minutes, not seconds) to avoid constant resource use.
- **Vision backend: open, unresolved.** A repo-level search of `oobabooga/text-generation-webui` for `image_url`/`multimodal` support found nothing, but that search was narrow; whether the actual running TextGen server/model exposes vision over its OpenAI-compatible API needs verifying hands-on, not by more code searching. If it doesn't work cleanly, the fallback is a separate dedicated local vision model/server behind its own swappable Protocol, matching `VectorStore`/`MemoryProvider`/`WebSearch`.
- **Cloud vision: opt-in only, not automatic** - unlike text models, where cloud is just a config swap (Round 10/`AgentCoreConfig`'s `cloud` extra), a screenshot is sensitive enough that sending it to a third party needs an explicit choice, not a silent default-off-but-swappable setting.
- **Capture scope: active/foreground window only**, not the whole desktop across all monitors - least exposure, and closest to what's actually relevant to a question about "what's on screen."
- **Persistence: never saved to disk by default** - captured, sent to the model, discarded. An optional debug flag to save the last screenshot for troubleshooting is in scope but off by default.

## Round 23
- **Approval Gate disconnected (Further Considerations' "Disconnect the Approval Gate," now resolved):** `propose_vault_change` is commented out of [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md)'s default tool list rather than removed outright - the tool, the approval-gate plumbing (Module H), and the Chainlit approve/edit/reject actions all still exist, just unwired, so re-enabling it later is a one-line change. Root cause: proposals paused via `interrupt()` become effectively unreachable if not resolved in the same chat session they were created in (a new chat has no way to see them), and the underlying LLM-as-judge review quality is weak on local models specifically - fixable with more work and/or cloud models, but not worth carrying broken in the meantime. Replacement for now: Kathrena just states suggested edits directly in her reply text, no tool/gate involved.
- **Broad env var rename, `KATHRENA_*` prefix dropped:** every module's env vars (`VAULT_ROOT`, `LLM_BASE_URL`, `PTT_HOTKEY`, `WEB_SEARCH_ENABLED`, etc.) lost their `KATHRENA_` prefix. Shorter and consistent with the generic names already used internally; accepted the small increase in collision risk with unrelated tools/libraries sharing the same shell/`.env`, since this is a single-user local project, not a shared/multi-tenant deployment.
- **General cleanup pass:** general review of in-flight work - stale docstrings/comments trimmed or corrected, `.files/` (Chainlit's runtime upload/audio cache, the same category of local runtime data as `/data/` and `/chroma/`) added to `.gitignore` and untracked.

## Round 24
- **`read_vault_file` added as a new always-available Module G tool:** `search_vault` only ever returns the top-k embedded *chunks* for a query (Round 5's chunking), not a whole file - relevant context elsewhere in the same note, or in a different section than the one that scored highest, was otherwise invisible to Kathrena even after `search_vault` pointed right at the file. `read_vault_file(path)` lets her escalate from excerpt to full file using the same path string `search_vault` already returns, the same two-step "search, then read" pattern as `search_memory`/`list_deadlines` needing no extra plumbing to discover what to read.
- **Deliberately ignores the `rag-index: false` opt-out:** that flag only controls what `search_vault`'s embeddings can surface unprompted, not whether a specific path - already known because another indexed note referenced it, or because `search_vault` itself surfaced it before opting out was set - can still be read directly. A file opted out of indexing is not a security boundary, just a "don't clutter embeddings with this" signal.
- **Path safety:** resolves `path` against `AgentCoreConfig.vault_root` and rejects anything that escapes it (`../`, absolute paths) via `Path.relative_to`, the same containment check `kathrena.rag_index.discovery`/`watcher` already rely on elsewhere in this codebase.
- **Size cap:** `AGENT_READ_FILE_MAX_CHARS` (default 20000) truncates oversized notes rather than risking blowing the context window in one tool call.
- **Windowed reads via `near_text` (same round, added after brainstorming the flat truncation cap's downsides):** rather than always reading from the top of the file, `read_vault_file` accepts the exact excerpt `search_vault` surfaced as `near_text`, locates it in the full file, and returns only `AGENT_READ_FILE_MAX_CHARS // 2` characters of padding on each side of it - reusing the existing size-cap knob rather than adding a second one. Falls back to the original truncated-full-file behavior if `near_text` is omitted or not found. Matching is whitespace/punctuation-insensitive (both sides normalized - lowercased, punctuation stripped, whitespace collapsed - before searching, then mapped back to the original text's own offsets) since a chunk's exact formatting can drift slightly from the source file.

## Round 25
- **Central settings store added (`kathrena.settings`), env vars dropped entirely:** every module's `_env_str`/`_env_int`/`_env_float`/`_env_bool`/`_env_path` helpers (byte-identical duplicates across 6 files) and every `os.environ.get(...)` call are gone. Every config dataclass field now reads its default through `kathrena.settings.setting_*(section, key, default)` instead - same `(name, default) -> value` call shape, different source. Chosen over keeping env vars as a fallback (the alternative considered) for a single, cleaner long-term source of truth, accepting that every module's README needed rewriting and that anyone's existing `$env:VAULT_ROOT = ...` workflow breaks.
- **File format: YAML at `./data/settings.yaml`** - `pyyaml` was already a dependency, no new package needed. Local runtime data, already covered by the existing `/data/` `.gitignore` entry.
- **Auto-migration via per-key lazy seeding, not whole-dataclass introspection:** `SettingsStore.value(section, key, default)` seeds and persists `default` the first time that specific key is ever read, and re-reads the file on every call so external hand-edits (or another part of the process calling `set_value`) are always picked up. This means a module adding a new field just shows up in the file on its next run, with no separate migration/schema step - simpler than reflecting on `dataclasses.fields()` (which would also fight `from __future__ import annotations`, since field types are strings unless resolved via `typing.get_type_hints`).
- **A shared `"common"` section for settings that were previously "shared by env var naming convention" across multiple modules** - `vault_root` (pipeline/agent_core/approval_gate/project_management/rag_index) and `llm_base_url`/`llm_model`/`llm_api_key` (pipeline/agent_core/memory) - preserving "set it once, every module picks it up" instead of splitting into 5 (or 3) independent per-module copies that would all need editing separately. Every other setting lives in its own module-scoped section (`agent_core`, `rag_index`, `chat_interface`, etc.).
- **Test isolation via an autouse fixture, not per-test env var patching:** `tests/conftest.py`'s `_isolated_settings_store` monkeypatches the module-level `kathrena.settings.store.settings` singleton to a fresh, `tmp_path`-backed `SettingsStore` for every test, so a bare `SomeConfig()` in any test reads/writes an isolated temp file instead of the real project's `data/settings.yaml`. Existing tests needed no changes beyond this, since they already construct configs with explicit kwargs for the fields they care about (confirmed by grepping for env var usage in tests/ - none found).
- **This is foundational, not yet the full ask:** named LLM profiles (local/cloud switch) and the AI-facing settings-changing tool are deliberately separate follow-up rounds, built on top of this store rather than folded into it.

## Round 26
- **Startup gate added (`kathrena.settings.bootstrap.ensure_configured`) after hitting the exact failure mode it's meant to prevent:** `vault_root`'s default (`.`) is silently plausible - it resolves to a real, existing directory (the project folder itself), so nothing errors, it just quietly points every module at the wrong place. Hit this directly (Round 25's settings migration): a running process had already captured the wrong `vault_root` before `data/settings.yaml` was hand-edited to the real path, and `read_vault_file` kept silently resolving against the project folder instead of failing loudly.
- **Only `vault_root` is hard-blocking**, not the LLM connection settings - a bad/default LLM endpoint fails loud (a connection error the moment Kathrena tries to respond), not silently wrong like a misdirected vault path, so it doesn't share the same risk profile. (Round 27 later removed the LLM trio this note originally also seeded here entirely, in favor of named `llm_profiles` resolved lazily by `kathrena.llm` instead.)
- **Placeholder is a descriptive sentinel string** (`"<< SET YOUR VAULT PATH HERE >>"`), not a bare `null`/absent key - keeps every consuming field's type untouched (`vault_root: Path`, not `Path | None` rippling into every reader), and is self-documenting if a user opens the file and sees it sitting there unedited.
- **Implemented on top of `SettingsStore.value()` directly**, no separate schema/registry needed - `ensure_configured()` just calls `.value()` for `vault_root` (seeding it into a brand new file if it doesn't exist yet) and checks whether it still equals the placeholder; everything else keeps using today's per-module lazy seeding unchanged.
- **Distinct message for "just created the file" vs. "file already existed but is still unconfigured"** - `SettingsStore.path.is_file()` is checked *before* seeding, so the two cases ("Created `data/settings.yaml` with default settings...") vs. ("`data/settings.yaml`'s `common.vault_root` is still unset...") give a first-time user and a returning-but-still-unconfigured user different, more actionable wording rather than one generic message for both.
- **Called once, at the very top of every real entry point** (`kathrena.chat_interface.app`, `kathrena.rag_index.__main__`, `kathrena.voice_log.pipeline`), before any other module's config is constructed - raises `SettingsNotConfiguredError`, which each entry point turns into `raise SystemExit(str(exc))` for a clean message instead of a raw traceback. Deliberately **not** wired into `kathrena.approval_gate.__main__`, which never touches the real vault by design.

## Round 27
- **LLM setup centralized into `kathrena.llm`:** the 3 duplicated `init_chat_model(...)` call sites (`voice_log.refinement.LangChainRefiner`, `agent_core.graph.build_agent_graph`, `memory.provider.LangMemProvider`) all hardcoded `model_provider="openai"` - meaning the existing `cloud` extra (`langchain-anthropic`) could never actually have worked, since Claude needs `model_provider="anthropic"`. Replaced with one `resolve_profile(name) -> LLMProfile` + `build_chat_model(profile)` pair; `build_chat_model` only passes `base_url`/`api_key` when set, so a real cloud call doesn't get a bogus local override.
- **Per-role profile switch (Option A from the original brainstorm), not a mid-turn local-decides/cloud-writes split (Option B):** `PipelineConfig` (Module E), `AgentCoreConfig` (Module G), and `MemoryConfig` (Module J) each dropped their own `llm_base_url`/`llm_model`/`llm_api_key` trio for a single `llm_profile: str = "local"` field, resolved independently - e.g. Module G can run on `cloud` for response quality while Module E/J stay on `local` for cheap, frequent background work. Option B (splitting tool-selection vs. final-answer generation across two models within one turn) stays explicitly out of scope - bigger graph restructure, a minimum of two model calls per turn instead of one, more risk for unclear benefit over the simpler per-role split.
- **Named profiles live in a new `llm_profiles` settings section**, not `common` - `common` remained for settings that are the same value everywhere (`vault_root`), whereas the whole point of profiles is that different roles resolve *different* profiles by name. `local` and `cloud` are both seeded (real working defaults for `local`; `cloud`'s `model`/`base_url`/`api_key` left unset) the first time *any* profile is resolved, so both show up ready to edit rather than only whichever one happened to be requested first.
- **`resolve_profile` raises rather than silently falling back** if a requested profile name doesn't exist, or exists but its `model` is still unset (the `cloud` starter's default state) - same "fail clearly instead of running against something silently wrong" principle as Round 26's `vault_root` gate, applied to LLM connections.
- **Only Module G is actually hot-swappable without a restart this round**, matching the "cheap subset only" scope decided earlier: `chat_interface.app._handle_turn` now constructs a fresh `AgentCoreConfig()` per turn (instead of reusing the frozen module-level singleton built once at import), and `build_agent_graph` already rebuilds its graph fresh every `run_turn()` call - so changing `agent_core.llm_profile` in `data/settings.yaml` takes effect on Kathrena's very next reply, no restart needed. Module E's `LangChainRefiner` and Module J's `LangMemProvider` still construct their chat model once at process start (a separate long-running pipeline process, and a module-level singleton in `chat_interface.app`, respectively) - their `llm_profile` changes remain restart-required, left as a Phase 3 candidate rather than solved here.

## Round 28
Design finalized this round (motivated by wanting to free the local GPU for gaming/rendering by switching Kathrena to cloud on request) - **implemented this round too**, 131 tests passing.

- **Reverses part of Round 27: the mid-turn local-decides/cloud-writes split ("Option B"), explicitly excluded back then, is now in scope** - the concrete ask ("cloud writes the reply, local still handles tool calls," aka "standard mode" below) can't be expressed as a single profile per role, since it needs *two different profiles for the same role* at once.
- **`AgentCoreConfig.llm_profile` splits into `tool_profile` and `reply_profile`:** `tool_profile` decides which tool(s) to call (bound with tools, loops through `call_tools` exactly as today); `reply_profile` writes the reply actually shown to the user.
- **The agent graph splits automatically based on whether the two differ, not from a stored "mode" flag:** when `tool_profile == reply_profile` (the default, and "local"/"cloud" modes below), the graph is *identical to today's* - one model, one node, no added cost. Only when they differ does `build_agent_graph` add a second `call_reply_model` node: once the tool-model's loop stops requesting tools, control passes *once* to the reply-model (not tool-bound, just writes text) for the actual final answer, then `END` - the tool-model's own "no tools needed" draft text is discarded, never shown. This keeps `local`/`cloud` modes exactly as cheap as before Round 28 - the extra round-trip only happens when the two profiles genuinely differ.
- **Module E and Module J adopt a "rebuild only on change" caching pattern** to become hot-swappable too: each remembers the name of the profile it last built its chat model from, and only reconstructs (chat model, and for Module J, the LangMem `manager`+`ReflectionExecutor`) when a fresh read of the current setting no longer matches - otherwise reuses the existing object untouched.
- **Module J's rebuild must explicitly `shutdown(wait=False)` the old `ReflectionExecutor` before replacing it - verified against LangMem's actual installed source (`langmem/reflection.py`), not assumed:** `LocalReflectionExecutor`'s cancel-and-resubmit debounce bookkeeping (`self._pending_tasks`) lives on the executor *instance*, so a freshly-built executor has no knowledge of a previous instance's scheduled jobs - confirming the risk is real, not hypothetical. More importantly, each executor also spins up its own non-daemon background thread that loops forever until `.shutdown()` is called - silently dropping the old executor without shutting it down would leak that thread permanently (and, being non-daemon, could even block a clean process exit). `.shutdown()`'s cleanup phase unconditionally invokes every still-queued reflection call regardless of cancellation state, so calling `shutdown(wait=False)` on the old executor doesn't just avoid the leak - it deterministically flushes any pending extraction immediately (using the pre-switch model), in the background, without blocking the turn that triggered the switch. A concrete, controlled mechanism rather than a vague "might duplicate" risk.
- **"Modes" are a write-once macro, not a stored setting** - `set_llm_mode(name)` just writes the 4 profile fields below per a fixed, hardcoded, in-code mapping (extensible later if a new LLM-using role is added); there's no persisted "current mode," so hand-editing one role's profile afterward is still fully supported, same as today.
  ```
  local:    pipeline=local, tool=local, reply=local,  memory=local
  cloud:    pipeline=cloud, tool=cloud, reply=cloud,  memory=cloud
  standard: pipeline=local, tool=local, reply=cloud,  memory=local
  ```
  `standard` keeps cheap/frequent background work (Module E/J) on `local`, spending cloud only on the part that's actually shown to the user.
- **Two tools, not one:** `set_llm_mode` (the fixed 3-value macro above) and a separate, more generic `change_setting` tool whose allow-list includes each profile field individually (`pipeline.llm_profile`, `agent_core.tool_profile`, `agent_core.reply_profile`, `memory.llm_profile`) - so the AI can also flip a single role's profile without applying a whole mode. Secrets/paths/`vault_root` remain excluded from that allow-list, unchanged from the original Phase 2 plan (Decisions Log's settings-tool entry, Further Considerations).
- **GPU-freeing scope explicitly limited to Kathrena's own request routing:** switching to `cloud`/`standard` stops Kathrena's own new requests to local TextGen, but does **not** unload TextGen's model from VRAM or stop the TextGen process itself (an external server this codebase doesn't control) - and doesn't touch RAG/memory embeddings, Whisper transcription, or Kokoro TTS, all of which stay local regardless of `llm_profile`/mode. Manually stopping/unloading TextGen (and anything else GPU-bound) remains a separate, manual step.

## Round 29
Addresses Further Considerations' last two open items ("Chat history reloaded on startup?" and
"Fix memory system overload") together, since making the first one true directly makes the
second one worse. **Chat-resume implemented this round** (133 tests passing); the memory-overload
fix is investigated/designed but deliberately **not implemented yet** - next step after this one.

- **Chat history already persisted before this round - just never looked up again.** `run_turn`'s
  `SqliteSaver` checkpoint already survives a process restart; the only reason the UI started
  blank every time was `on_chat_start` minting a brand-new random `thread_id` on every call. This
  reframed "add chat history persistence" down to "pick a thread_id worth resuming, and replay it."
- **Considered Chainlit's own native data layer (`BaseDataLayer`/`SQLAlchemyDataLayer`) first,
  investigated it thoroughly, and explicitly deferred it** - see
  [Chainlit Data Layer](Investigations/Chainlit%20Data%20Layer.md) for the full write-up (schema, deps,
  method surface). The disqualifying finding, confirmed against Chainlit's own docs and source,
  not assumed: thread resume **requires authentication to be enabled** (`on_chat_resume`/chat
  history both explicitly require it) - Chainlit's `Thread` model is fundamentally scoped to a
  user identifier, there's no anonymous-persisted-thread path. Adopting it would mean adding an
  auth layer (even an invisible always-succeeding one), two new dependencies
  (`sqlalchemy`/`aiosqlite`), and a hand-maintained external SQL schema (Postgres-flavored, not
  bundled in the pip package) to an app explicitly designed as a single zero-auth local process.
  Kept on file for a future pass if the native thread-history sidebar ends up worth that cost.
- **Went with the lighter alternative instead:** `on_chat_start` reads a persisted
  `agent_core.last_thread_id` setting; if that thread isn't already claimed by another open tab
  this run (tracked in a module-level `_active_thread_ids` set), it's resumed - otherwise, same as
  before, a fresh `uuid4()` thread starts. `kathrena.agent_core.graph.load_thread_messages` reads
  a thread's messages directly off the raw LangGraph checkpoint (`checkpointer.get_tuple(...)`)
  without building the full graph/tools/chat model just to peek at history. `_replay_history`
  re-sends each past Human/AI turn (not tool calls/outputs) as a normal `cl.Message` so the
  resumed UI looks continuous. A second tab open at the same time still gets its own fresh
  thread - only a genuine restart resumes. See [K - Chat Interface](Modules/K%20-%20Chat%20Interface.md).
- **Known rough edge, not special-cased:** in a "split" tool/reply-profile conversation (Round 28's
  `standard` mode), the tool-model's own discarded draft reply also carries non-empty content and
  would replay as an extra visible line on resume - rare enough in practice not to filter out yet.
- **Memory-overload fix investigated, not implemented:** full write-up at
  [Memory Context Management](Investigations/Memory%20Context%20Management.md). Two independent,
  composable pieces recommended once it's time to build this: (1) `langchain_core.messages
  .trim_messages` (message-count window, `start_on="human"`) capping only what the live
  `call_model`/`call_reply_model` nodes actually send to the LLM each turn, leaving the
  checkpointed state itself untouched; (2) a trim-once-too-long cap (not a precise
  submit-time watermark) on what Module J's `remember()` re-sends to LangMem each call. The
  precise "watermark that advances on every submit" version from the original Further
  Considerations note was checked against LangMem's actual debounce/cancellation mechanics
  (already verified for Round 28) and found to have a real correctness gap: a cancelled
  submission's range could end up permanently skipped if the watermark had already advanced past
  it. The threshold/keep-window alternative avoids depending on any specific submission having
  actually run at all.

## Round 30
Implements [Memory Context Management](Investigations/Memory%20Context%20Management.md) - both pieces,
137 tests passing. Revises Round 29's own recommendation for Module J's part after finding a way
to make the precise version safe, rather than settling for the cruder trim-when-too-long
fallback.

- **Part 1 (live prompt) built as designed:** `build_agent_graph` now has a shared
  `_windowed_prompt(state)` helper, used by both `call_model` and `call_reply_model`, that runs
  `langchain_core.messages.trim_messages(state["messages"], strategy="last", token_counter=len,
  max_tokens=config.history_window_messages, start_on="human")` before prepending the system
  prompt - `token_counter=len` verified against `trim_messages`'s actual source to confirm it
  really does behave as a message-count window (not a real per-message token count) for exactly
  the reason Round 29 wanted: no tokenizer that has to stay accurate across whichever local/cloud
  model is in play for a role. New `AgentCoreConfig.history_window_messages` (default `12`). The
  checkpointed state itself is untouched - only the prompt built per call is capped.
- **Part 2 (memory)** upgraded from "trim-when-too-long" to the precise marker after confirming it
  actually is safe, not just theoretically nicer: `LangMemProvider` now persists a per-thread
  marker (`("memory_markers",)` namespace in the same `SqliteStore` already kept open for the
  process's lifetime) via plain `BaseStore.get`/`put`. `remember()` submits only
  `messages[marker - overlap:]`, and advances the marker from the submission's own
  `future.add_done_callback(...)` rather than at submit time - `only if not future.cancelled()`.
  This closes Round 29's documented gap directly: LangMem's `ReflectionExecutor.submit()` returns
  a real `concurrent.futures.Future`; tracing `_process_queue` confirmed a superseded submission
  has `.future.cancel()` called on it and resolves `cancelled()` without ever invoking the
  reflector, while the one submission that actually survives resolves via `set_result(...)` - a
  concrete, checkable signal for "this exact range was truly processed," verified against
  LangMem's installed source rather than assumed. New `MemoryConfig.marker_overlap_messages`
  (default `2`). No message range can be silently skipped the way a submit-time-advanced marker
  could - every message eventually reaches LangMem via *some* submission.
- **Why the precise version over the simpler fallback, now that it's confirmed safe:** the
  trim-when-too-long alternative permanently drops old, never-yet-extracted material once
  trimmed; the marker design sends each message to LangMem exactly once (plus the small
  deliberate overlap) with no such loss, and costs nothing extra to build once the
  completion-callback mechanism is in hand. Kept on file in
  [Memory Context Management](Investigations/Memory%20Context%20Management.md) as a documented fallback
  only.
- **Verified, not just inferred, that Module J's existing profile-switch rebuild (Round 28)
  doesn't break this:** `shutdown(wait=False)`'s "drain the queue" phase force-runs any
  still-queued submission regardless of its cancel state, which still resolves the future via
  `set_result(...)` - the done-callback still fires and the marker still advances correctly
  across a mid-conversation profile switch.

## Round 31
Two independent, small fixes requested together, both implemented this round, 141 tests passing.

- **Token limits:** `LLMProfile` gained a `max_tokens: int | None = None` field, read from each
  named profile's own `llm_profiles.<name>.max_tokens` and passed to `init_chat_model` only when
  set (same "only pass what's actually configured" pattern as `base_url`/`api_key`) - one place
  (`kathrena.llm.build_chat_model`), applies to every role (Module E/G/J) automatically. Prompted
  by a real incident (Further Considerations' "Token limits" note): an uncapped cloud reply came
  back very large and costly without being useful. `cloud`'s seeded default is `8192` (a cap,
  since cloud tokens cost real money); `local`'s stays `None` (uncapped - no per-token cost, and
  already bounded by local hardware/time).
- **Migration gap found and fixed while implementing this:** `SettingsStore`'s per-key auto-seed
  (Round 25) only seeds a whole `(section, key)` pair the first time *that key* is missing - but
  `llm_profiles.<name>` is one key holding a nested dict, so adding `max_tokens` to
  `_DEFAULT_PROFILES` would never have reached an *already-seeded* profile (e.g. this project's
  own already-running `cloud` profile) without explicit handling. `seed_default_profiles` now
  also backfills any default sub-key missing from an already-existing profile dict, leaving
  already-customized fields (`model`/`api_key`/etc.) untouched - otherwise the fix wouldn't have
  actually applied to the exact installation that surfaced the problem.
- **System prompt moved to config:** `AgentCoreConfig.system_prompt` (default: the existing
  personality/behaviour text, `agent_core.system_prompt` in `data/settings.yaml`) replaces the
  old hardcoded `_BASE_SYSTEM_PROMPT` module constant in `kathrena.agent_core.graph` - editable
  without touching code, per Further Considerations' "Move the system prompt to config" note.
  **Only the non-tool (personality/behaviour) portion moved** - the sentence describing the
  always-available tools (`search_vault`/`read_vault_file`/`get_current_datetime`/`set_llm_mode`/
  `change_setting`) stays hardcoded as `_TOOLS_SYSTEM_PROMPT_ADDITION` in `graph.py`, appended
  after `config.system_prompt` at build time, same as the existing conditional
  `_MEMORY_SYSTEM_PROMPT_ADDITION`-style additions - so hand-editing the personality text can
  never accidentally describe tools that aren't actually wired up (or omit ones that are).

## Round 32
Two independent features requested together, both implemented this round, 146 tests passing.
Both went through a "sketch it first" design pass before any code, per request - see the research
notes below for findings that changed the plan mid-sketch.

- **Reveal thinking:** `_handle_turn` (`chat_interface/app.py`) now builds a fresh
  `cl.LangchainCallbackHandler()` per turn and passes it into `run_turn(..., callbacks=[...])`,
  which attaches it to the graph run's own `RunnableConfig` - Chainlit's built-in handler turns
  the run's LLM calls into visible nested UI steps automatically, no hand-rolled `cl.Step` code
  needed for that part. Verified (not assumed) that this works correctly even though `run_turn`
  is invoked synchronously via `cl.make_async`: traced LangChain's sync callback dispatch
  (`langchain_core/callbacks/manager.py`'s `handle_event`/`_run_coros`) and confirmed it bridges
  to the handler's async-only methods via a fresh `asyncio.Runner()` - and Chainlit's own docs'
  "Sync LCEL" example shows this exact `cl.make_async(...) + cl.LangchainCallbackHandler()`
  pairing as an officially supported pattern, not a guess.
- **Tool calls needed real surgery, not just the callback handler, to show up at all:**
  `call_tools` was manually invoking plain Python functions (`fn(**call["args"])`) rather than
  going through LangChain's `Runnable` protocol - so no `on_tool_start`/`on_tool_end` callback
  ever fired for a tool call, regardless of which handler was attached. First proposed a hybrid
  (handler for LLM calls + hand-rolled `cl.Step`s just for tools), but asked and the answer was
  "switch tool calls through the Runnable protocol properly" instead. Implemented by wrapping
  each tool factory's returned function with `langchain_core.tools.tool()` where `build_agent_graph`
  collects them into its `tools` list (not inside `agent_core.tools.py`'s factories themselves -
  smallest blast radius), and calling `tool_obj.invoke(call["args"], config=config)` instead of
  calling the raw function - `call_model`/`call_tools`/`call_reply_model` all gained an explicit
  `config: RunnableConfig` second parameter (LangGraph's standard "node wants the run config"
  convention) threaded down to every `.invoke()` call, rather than relying on LangChain's ambient
  `var_child_runnable_config` contextvar propagating it implicitly - more code, but no guessing
  about whether tool-call events nest under the right run. `PendingReview`/error-handling in
  `call_tools` needed no changes: `BaseTool.invoke()` passes through a wrapped function's raw
  return value and re-raises exceptions unchanged, same as calling it directly.
- **Log input and output messages for tooling and LLM:** new `kathrena.llm_logging` module -
  `kathrena.llm_logging.with_logging(model, label)` binds a `LoggingCallbackHandler` via
  `.with_config(callbacks=[...])`, so every subsequent call that chat model makes gets logged.
  Must be applied *last*, after `.bind_tools()`/any other composition: `bind_tools()` on an
  already-`.with_config()`-bound model silently discards the earlier binding
  (`RunnableBindingBase.__getattr__` only forwards bound config through methods whose own
  signature accepts a `config` kwarg; `bind_tools` has none) - verified directly in
  `langchain_core`'s source, and confirmed by tracing a real `on_chat_model_start` call that
  silently never fired with the wrong ordering, then did once reordered. `build_agent_graph` now
  does `with_logging(chat_model.bind_tools(tools), "agent_core.tool")`. Scoped to Module G
  (`"agent_core.tool"`/`"agent_core.reply"`) and Module J only, by request - Module E's refiner
  stays unlogged. Tool call input/output logged directly inside `call_tools` instead (it already
  invokes tools itself; no callback machinery needed there). Added a real `BaseChatModel`
  subclass (not a bare stand-in) to the test suite specifically to reproduce `bind_tools()`'s
  actual behavior - mocked fakes alone don't exercise a real `.bind_tools()` call, so they can't
  catch an ordering bug like this one.
- **Module J needed a different approach:** LangMem's own `create_memory_store_manager` rejects
  anything that isn't a plain `BaseChatModel`, so wrapping its model via `with_logging(...)` (even
  applied last) crashes on startup. Instead, `remember()` attaches the logging callback
  per-submission via `self._executor.submit(..., config={"callbacks": [...]})`, relying on
  LangMem's own ambient `var_child_runnable_config` propagation - the model itself stays
  unwrapped.
- **Log rotation:** `logging.handlers.TimedRotatingFileHandler(when="midnight", backupCount=10)` -
  one file per calendar day, unlimited size within a day, last 10 days kept automatically, by
  request. Plain text, one shared file (`data/logs/llm_calls.log`) for every labeled role.

## Round 33
- **Real bug found in production use:** after the RAG indexer picked up a newly-added vault file,
  `search_vault` couldn't find it until the chat app was restarted - then it worked instantly.
  Root cause: the chat app and the indexer are two independent OS processes (`start.ps1`), and
  each previously opened its own embedded Chroma `PersistentClient` pointed at the same
  `persist_directory`. A long-lived client in one process doesn't see writes a *different*
  process made to the same on-disk files - only a fresh client, built after a restart, re-reads
  from disk and sees them.
- **Fix: a single shared `chroma run` server process**, with both the chat app and the indexer
  connecting to it via `chromadb.HttpClient` instead of each embedding their own client. One
  authoritative process owns the actual index state; everyone else is just a client of it - the
  textbook-correct shape for "multiple processes need to share one vector index live", not a
  workaround. `start.ps1` now launches the server first, with a short head start before its
  clients (the chat app, the indexer) start trying to connect.
- **Two alternatives considered and rejected:** merging the indexer's watcher into the chat app
  process itself (same process, background task, like push-to-talk) would also fix it - no
  cross-process visibility problem if there's only one `ChromaVectorStore` instance - but reverses
  the deliberate choice that the voice-log pipeline and F's watcher stay independent of the live
  chat agent, needing only disk access to the vault. A narrower patch (reconnect a fresh client
  per `search()` call, keeping the embedding model cached) was also considered - cheaper to write,
  but doesn't fix the actual multi-process model, just papers over this one symptom.
- **Connection retry, not a hard failure on first attempt:** since `start.ps1` launches the server
  and its clients together, a client can easily try to connect before the server's finished
  starting up. `ChromaVectorStore` retries (`rag_index.chroma_connect_retries`, default 10, 1s
  apart) and calls `.heartbeat()` to confirm the server's actually responsive, not just that the
  port happened to accept a TCP connection.