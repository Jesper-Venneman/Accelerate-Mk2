Open questions to resolve before turning [Accelerate Mk2](Accelerate%20Mk2.md) into a build-ready plan. Expand each section as we make progress - this note is meant to grow.

## ~~Tech stack~~ (resolved)
Vector store: Chroma. Embedding model: BAAI/bge-small-en-v1.5. Wake-word engine: openWakeWord. All free/local, no paid tiers - see [Decisions Log](Decisions%20Log.md). Relevant to [F - RAG Indexing Module](Modules/F%20-%20RAG%20Indexing%20Module.md) and [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md).

Orchestration framework: **resolved** - LangGraph, see [Decisions Log](Decisions%20Log.md). RAG implementation stack: **resolved** - LangChain components orchestrated by LangGraph, see [Decisions Log](Decisions%20Log.md).

## ~~Kathrena's personality~~ (resolved)
Warm and casual tone; a mix of task-focused (logs/project-management) and companion-like (open conversation); diplomatic when she disagrees; occasional light humor. This is Kathrena's first LLM-backed "brain" behind her long-running, evolving interface. See [Decisions Log](Decisions%20Log.md) and [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md).

## ~~Kathrena's long-term memory~~ (resolved)
A background memory-formation agent (LangMem, on LangGraph's native `Store`) extracts and categorizes memories into a dedicated store kept separate from the vault, with its own semantic search. See [Decisions Log](Decisions%20Log.md) and [J - Memory Module](Modules/J%20-%20Memory%20Module.md).

## ~~Per-project RAG opt-out mechanism~~ (resolved)
Confirmed: a frontmatter flag next to `synonyms:`, e.g. `rag-index: false`. Not critical, but cheap to implement, so worth doing. See [Decisions Log](Decisions%20Log.md) and [F - RAG Indexing Module](Modules/F%20-%20RAG%20Indexing%20Module.md).

## ~~Task-tracking conflict resolution~~ (moot - feature cut)
Task/checklist tracking (I1) is cut from scope for now rather than resolving this. See [Decisions Log](Decisions%20Log.md) and [I - Project Management Modules](Modules/I%20-%20Project%20Management%20Modules.md).

## ~~Approval-gate review UI~~ (resolved)
Chat window for v1; a dedicated Obsidian plugin is a planned phase-2 enhancement. See [Decisions Log](Decisions%20Log.md) and [H - Change Proposal and Approval Gate](Modules/H%20-%20Change%20Proposal%20and%20Approval%20Gate.md).

## ~~Local LLM runtime and model~~ (resolved)
Local runtime: oobabooga's **TextGen** (formerly text-generation-webui) - already in use, free/AGPL-3.0, 100% offline/private, exposes an OpenAI/Anthropic-compatible API with tool-calling support, supports swapping backends/models (GGUF/EXL3/Transformers) without restarting. Cloud connector: LangChain's `init_chat_model()` plus the relevant provider package (`langchain-openai`, `langchain-anthropic`, etc.) - the same abstraction already used everywhere else, so switching local/cloud is just a config change. Specific model deliberately left unpinned/swappable. See [Decisions Log](Decisions%20Log.md) and [E - Refinement and Summarization Module](Modules/E%20-%20Refinement%20and%20Summarization%20Module.md).

## ~~Transcription engine choice~~ (resolved)
faster-whisper (MIT, CTranslate2-based) - up to 4x faster than plain `openai-whisper` with less memory, same accuracy. See [Decisions Log](Decisions%20Log.md) and [B - Transcription Module](Modules/B%20-%20Transcription%20Module.md).

## ~~Flesh out I2, I3, I5~~ (deferred by design)
Deliberately left at their current implementation-pattern level (skill vs. sub-agent, see [I - Project Management Modules](Modules/I%20-%20Project%20Management%20Modules.md)) rather than fully speccing them now. Deeper specs (tool signatures, I3's scheduling details, etc.) wait until [F - RAG Indexing Module](Modules/F%20-%20RAG%20Indexing%20Module.md) and [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md) are built and we've seen how they actually perform - see [Decisions Log](Decisions%20Log.md).

## ~~Chat interface module~~ (resolved)
Chainlit (Apache-2.0, pure Python, self-hosted) - `cl.Action` buttons implement approve/reject/edit against [H - Change Proposal and Approval Gate](Modules/H%20-%20Change%20Proposal%20and%20Approval%20Gate.md)'s `interrupt()`/`Command(resume=...)` flow. See [Decisions Log](Decisions%20Log.md) and [K - Chat Interface](Modules/K%20-%20Chat%20Interface.md).

## ~~Runtime/deployment architecture~~ (resolved)
One long-running Python process embeds LangGraph directly, no separate server/CLI/LangSmith account. See [Architecture Overview](Architecture%20Overview.md#runtime-architecture) and [Decisions Log](Decisions%20Log.md).

## ~~Wake-word vs voice-log recording distinction~~ (resolved)
Confirmed separate: [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md)'s always-on wake-word listener and [A - Ingestion and Sync Layer](Modules/A%20-%20Ingestion%20and%20Sync%20Layer.md)'s voice-log recording are two independent microphone-capture flows for two different purposes.

## Screen perception vision backend (open)
Blocking [L - Screen Perception Module](Modules/L%20-%20Screen%20Perception%20Module.md): whether the project's TextGen server/loaded model
actually exposes vision/multimodal input over its OpenAI-compatible API in a form
`langchain-openai` can drive. A repo-level search of `oobabooga/text-generation-webui` found no
`image_url`/`multimodal` support, but that search was narrow and inconclusive - needs verifying
hands-on against the real running server, not more code searching. Fallback if it doesn't work
cleanly: a separate dedicated local vision model/server. See [Decisions Log](Decisions%20Log.md) Round 22.

## Disconnect the Approval Gate (resolved)
The approval gate has issues like approvals becoming headless if they are not approved within the chat they are created. A new chat won't have access.
They also perform poorly on local models, further refinement could fix this, using cloud models for sure, but for now we will disconnect the module and
replace it with simply suggestions in the AI response, no direct file modification, no tool needed. based on suggestions.

## ~~Full file retrieval~~ (resolved)
I noticed that some questions are answered with file contents, but not all contents of that file are listed, even if they may be relevant.
Added a `read_vault_file` tool so Kathrena can retrieve a note's full contents after `search_vault` points at a promising file. See [Decisions Log](Decisions%20Log.md) Round 24 and [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md).

## ~~Add switch between local and cloud models~~ (resolved)
We need a switch to go between local and cloud models, so depending on the workload we can go for a simpler cheap local model, and for more intense workload go for a cloud model.
Also allows switching when the gpu is used of other tasks, e.g. rendering, gaming.
Added `kathrena.llm`'s named `llm_profiles` (`local`/`cloud`), picked independently per role via each config's profile field(s). See [Decisions Log](Decisions%20Log.md) Round 27.
Round 28: Module G's single `llm_profile` split into `tool_profile`/`reply_profile` so tool-calling and reply-writing can use different profiles at once ("standard mode" below); Module E/J gained a "rebuild only if the profile actually changed" cache, so all three roles are now hot-swappable without a restart.

## ~~Centralize LLM setup~~ (resolved)
Currently multiple LLM connections are set up in different components, these could be centralized and it would probably help with the local/cloud switch.
The 3 duplicated `init_chat_model(...)` call sites are now `kathrena.llm.resolve_profile`/`build_chat_model`, one place - see [Decisions Log](Decisions%20Log.md) Round 27.

## ~~Add central config file~~ (foundation resolved, phase 1 of 3)
We need a config file that is loaded when the program starts, it should set the configs of all the modules, and be updated automatically on startup if any new module adds new configuration settings.
Each module can keep a set of basic settings that can be used when there is no set configuration for them, these settings can also be used as placeholder when adding the new fields to the config.
Added `kathrena.settings` - every module's config now reads its defaults from `data/settings.yaml` instead of env vars, auto-seeding any new field the first time it's read. Env var support was dropped entirely rather than kept as a fallback. See [Decisions Log](Decisions%20Log.md) Round 25. The local/cloud LLM profiles and the AI-facing settings tool (both above/below) build on this and are now done too.

## ~~Add tool calling for config changes~~ (resolved)
Allow the AI to switch/update settings through the chat/voice interface using a tool. Tool should provide a list of settings and their purpose so that the AI can decide which settings the user meant.
Settings are then updated to the user desired value. Along with this function hot swapping of many setting should be made possible so that the entire ui does not need to reload/restart when settings change.
This is especially useful for the LLM endpoint, allowing easy swapping when the gpu is going to be used.
Two tools (Decisions Log Round 28): `set_llm_mode("local"|"cloud"|"standard")` (a fixed macro over 4 profile fields) for the concrete GPU-freeing case, plus a separate, more generic `change_setting` tool whose allow-list includes those same profile fields individually. Secrets/paths/`vault_root` stay excluded from that allow-list. GPU-freeing is scoped to Kathrena's own request routing only - doesn't unload TextGen's model/VRAM or touch embeddings/Whisper/Kokoro, all of which stay local regardless. See [G - Kathrena Agent Core](Modules/G%20-%20Kathrena%20Agent%20Core.md).

## ~~Chat history reloaded on startup?~~ (resolved, lighter version)
Questionable, but it might be useful to have the chat history reload from the previous state when the ui is restarted. Current designs are not meant for that, as it will conflict with the THREAD_ID 
and mainly memory implementation. Memory system reads full chat each time, systems will need to be in place to actually manage this better because after this change it will become a significant enough problem.

A restart now resumes the last active conversation: `on_chat_start` persists/reuses a `agent_core.last_thread_id` setting and replays the resumed thread's messages from the existing LangGraph checkpoint - no new storage, no Chainlit data layer. The fuller native option (thread-history sidebar, multi-thread switching) was investigated and documented but deliberately not built, since it requires adding an authentication layer to an otherwise zero-auth app - see [Chainlit Data Layer](Investigations/Chainlit%20Data%20Layer.md) and [Decisions Log](Decisions%20Log.md) Round 29.

## ~~Fix memory system overload~~ (resolved)
Fix memory system taking in the full history of the chat. Implement a system to trim the chat, mark messages as memorized(possibly with overlap for reinforcement), or a mix of both.
Currently this is not a major issue due to short chats in the testing phases, but when complete this system is designed to run alongside the device constantly, leading to way larger chats.

Implemented in two parts (Decisions Log Round 30): `agent_core.history_window_messages` caps what the live model sees each turn via `trim_messages`, and a persisted per-thread marker in Module J caps what `remember()` re-submits to LangMem, advancing only once a submission is confirmed to have actually run (not just been submitted) - verified safe against LangMem's actual debounce/cancellation source. See [Memory Context Management](Investigations/Memory%20Context%20Management.md) and [Decisions Log](Decisions%20Log.md) Round 30.

## ~~Token limits~~ (resolved)
Currently it seems tokens are uncapped I think, had an instance where the output of the cloud llm was very large significantly more costly without the output being anything useful, which is bad, need to prevent these.

`LLMProfile` gained `max_tokens`, read per named profile and passed to `init_chat_model` only when set - applies to every role (Module E/G/J) through the one centralized `kathrena.llm.build_chat_model`. `cloud` now seeds with a `8192` cap by default (cloud tokens cost money); `local` stays uncapped (no per-token cost). See [Decisions Log](Decisions%20Log.md) Round 31.

## ~~Move the system prompt to config~~ (resolved)
Gotta move the non-tool system prompt part to config so users can edit it.

`AgentCoreConfig.system_prompt` (`agent_core.system_prompt` in `data/settings.yaml`) now holds the personality/behaviour text - editable without touching code. The tool-availability sentence stays hardcoded in `kathrena.agent_core.graph`, appended after the configured prompt, so it can't drift out of sync with which tools are actually registered. See [Decisions Log](Decisions%20Log.md) Round 31.

## ~~Prevent multiple instances~~ (Won't fix)
Multiple instances register multiple hotkeys, bad...

Skill issue, don't open multiple tabs dummy! The fix for this would be too complex for now to be worth it, if this becomes an actual issue it may be revisited.

## ~~Reveal thinking~~ (resolved)
Reveal thinking and tool use in the chainlit app

A fresh `cl.LangchainCallbackHandler()` per turn turns LLM calls into visible nested UI steps automatically. Tool calls needed more than that: `call_tools` used to invoke plain Python functions directly (bypassing LangChain's callback system entirely), so tools were wrapped with `langchain_core.tools.tool()` and invoked via `.invoke(args, config=config)` instead, with an explicit `config: RunnableConfig` threaded through every node - so tool calls now show up as real callback-driven steps too, not just LLM calls. See [Decisions Log](Decisions%20Log.md) Round 32.

## ~~Log input and output messages for tooling and LLM~~ (resolved)

New `kathrena.llm_logging` module: `kathrena.llm_logging.with_logging(model, label)` binds a logging callback, applied *after* `.bind_tools()`/any other composition (an earlier ordering bug silently dropped it otherwise) - covers Module G (tool/reply profiles). Module J attaches the callback per-submission instead, since LangMem rejects a wrapped model. Module E's refiner stays unlogged. Tool call input/output logged directly inside `call_tools`. Plain text, one shared file (`data/logs/llm_calls.log`), rotated daily at midnight with the last 10 days kept. See [Decisions Log](Decisions%20Log.md) Round 32.

## Make use of the chainlit datalayers instead of current thread id and sqlLite db solution
Allows for the use of different chats, new chats to separate between topics.

## Reimplementation of the note change suggestions
The previous 'Approval Gate' solution was not that great with local models, and generally was cumbersome to use. Ideally a new solution is created to fill this gap as the functionality is still very useful. A proposed solution would be that the AI is capable of suggesting changes to the notes(as before), but instead of handling these changes here, they are handled in Obsidian, ideally with a similar system as seen in Visual Studio Code with AI suggested changes, allowing keep and discard options or allowing the user to edit the changes. For this, a new plugin is likely needed, unless an existing plugin exists that can sufficiently fill this purpose.

## Reimplementation of the note change suggestions
Add (API) connections to other services to keep up to date on other stuff outside the vault.
- Mail
- Investments
- News
- LinkedIn? mail may be enough

## Screen perception
Allows the agent to view the screen and react on it's contents. Currently limited by incomplete tests with image capable models.

## Independent functioning
Allows the agent to function independently based on external inputs, like the before mentioned (API) connections and screen perception.

## Implement and endpoint to connect a virtual avatar to. -- Stretch goal
Connect the existing avatar to this project using an endpoint that can move the shape keys of the model.