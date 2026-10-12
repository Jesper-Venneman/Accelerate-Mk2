Gives [Kathrena](G%20-%20Kathrena%20Agent%20Core.md) a persistent, evolving memory - separate from the vault knowledge in [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md) - so she learns about you and your interactions over time, not just retrieves vault content.

## Responsibilities
- A separate background memory agent reviews conversations (not part of the live response turn) and decides what's worth remembering, then extracts and categorizes it - e.g. facts about people and preferences (semantic memory) vs. past events/experiences (episodic memory).
- Memories are written to a dedicated store, kept separate from the Obsidian vault - personal/relational memory never mixes into vault search results or gets exposed via [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md).
- The memory store supports semantic search of its own, so [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md) can recall relevant memories at any time, not just within the current conversation thread.
- Kathrena reads from both this module and [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md) when reasoning - vault RAG for project/vault knowledge, this module for personal/relational memory - so she becomes an evolving entity that learns from her surroundings.

## Implementation approach
Built on LangGraph's native long-term memory `Store` - memories are JSON documents under a namespace (like a folder) and a key (like a filename), with built-in semantic search, the same execution family already used for [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md)'s checkpointer.

**LangMem** (MIT license, LangChain team, free) provides exactly the pattern you described: a background memory manager that "automatically extracts, consolidates, and updates agent knowledge" - the separate memory-formation agent - plus optional hot-path tools (`create_manage_memory_tool` / `create_search_memory_tool`) if Kathrena should ever save something mid-conversation instead of only in the background.

The backing store is **`langgraph.store.sqlite.SqliteStore`** (bundled inside the already-installed `langgraph-checkpoint-sqlite` package - zero new dependencies) rather than Chroma: it's a persistent, file-based `BaseStore` with built-in vector search (via `sqlite-vec`), so it needed no custom adapter code at all. It lives in its own SQLite file (`data/memory.sqlite`, separate from both the vault's Chroma collection and [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md)'s checkpointer database), kept open for the process's lifetime rather than opened per-call, since it's internally thread-safe. Embeddings reuse the same model as [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md) (`BAAI/bge-small-en-v1.5`), but a fully separate instance/database - personal memory is deliberately kept out of vault search results.

**Modularity constraint:** LangMem must sit behind a swappable memory-provider interface (extract/store/search operations only) rather than being called directly throughout [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md) and this module. This keeps the door open to replace it with a custom-built memory implementation later without a redesign. Implemented as a `MemoryProvider` Protocol (`recall(query)` / `remember(messages, thread_id)`) with a `LangMemProvider` concrete implementation, matching the same swappable-Protocol pattern already used for [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md)'s `VectorStore` and [K - Chat Interface](K%20-%20Chat%20Interface.md)'s `TextToSpeech`/`VoiceEffects`.

**Hot-swappable LLM profile without a restart (Decisions Log Round 28):** `LangMemProvider` remembers which profile it last built its chat model from, and only rebuilds (chat model, `manager`, and `ReflectionExecutor`) when a fresh read of `memory.llm_profile` no longer matches - never on every `remember()` call. Verified directly against LangMem's installed source rather than assumed: `ReflectionExecutor`'s cancel-and-resubmit debounce bookkeeping lives on the executor instance itself, and each instance also owns a non-daemon background thread that runs until explicitly shut down - so the rebuild calls `shutdown(wait=False)` on the *old* executor before replacing it, avoiding the leak. Doing so also deterministically flushes any still-pending extraction immediately (using the pre-switch model, in the background, non-blocking) rather than leaving it in an unclear state - `shutdown()`'s cleanup phase runs every queued job regardless of cancellation status.

**Call logging (Decisions Log Round 32):** `remember()` attaches the logging callback per submission via `self._executor.submit(..., config={"callbacks": [...]})`, not by labeling the model itself - `build_chat_model`'s `log_label` wrapping would break LangMem's own internal model-type check.

## Considered and rejected
**Mem0** - also has an OSS core (Apache-2.0), but its defaults point at paid OpenAI APIs (`gpt-5-mini`, `text-embedding-3-small`) unless reconfigured, and its self-hosted tier deliberately withholds "advanced features" for the paid cloud platform. Worse fit for the no-paid-options rule than LangMem, which has no commercial tier at all.

## Categorization (current: simplified, single-namespace)
For this pass, memories are unstructured/schema-less documents in a single fixed namespace (`("memories", "kathrena")`), rather than the fuller LangMem memory-type framework originally planned. **Deferred** to a later pass (see Decisions Log Round 19):
- **Semantic - Profile:** a single, continuously-updated document for the user's own core facts/preferences (e.g. name, communication preferences) - easy to look up, always current.
- **Semantic - Collection:** separate documents for facts about *other* people and general knowledge, since there can be many of them and none should be lost.
- **Episodic:** summaries of past conversations/interactions (situation, reasoning, outcome), so Kathrena can recall how a past discussion went, not just isolated facts.

This simplification keeps `create_memory_store_manager`'s extraction (no custom schema) and a single `store.search(...)` call for recall - the taxonomy above remains the design target once the simpler version is proven out.

## Formation trigger
Uses LangMem's `ReflectionExecutor` ("Defer Background Memory Processing" pattern) - debounced background processing that waits until a conversation goes idle for a bit before extracting memories, rather than after every message (expensive) or a rigid schedule. Because the debounce cancels/reschedules per `thread_id` (only the last submission before idle actually runs), [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md)'s `run_turn` passes the *full* accumulated conversation history on every turn, not just the latest exchange, so whichever submission finally executes still sees the whole conversation.

## Retention
Relies on LangMem's built-in behavior rather than a custom expiry policy: its memory manager already reconciles new information against existing memories - updating, consolidating, or removing outdated ones - and Collection retrieval ranks by similarity plus "importance" and "strength" (recency/frequency of use), so stale memories naturally rank lower even without hard deletion. Revisit with an explicit hard cap/expiry only if memory volume turns out to be a real problem in practice.

## Deferred: chat transcript reload
Reloading the actual chat transcript/session (as displayed in [K - Chat Interface](K%20-%20Chat%20Interface.md)) across app restarts is a separate feature from this module's own semantic memory - now implemented, see [K - Chat Interface](K%20-%20Chat%20Interface.md) and Decisions Log Round 29.

## Bounded re-submission to LangMem (Decisions Log Round 30)
`remember()` no longer hands LangMem the *entire* conversation on every call. A persisted per-thread marker (`("memory_markers",)` namespace in the same `SqliteStore` used for memories) tracks how many messages have been *confirmed* handed to LangMem, so each call only submits the unsent tail plus a small overlap (`memory.marker_overlap_messages`, default `2`) for continuity. The marker only advances from the submission's own completion callback, not at submit time - verified against LangMem's installed source that a submission superseded by `ReflectionExecutor`'s debounce resolves as `cancelled()` without ever running, while one that actually executes resolves normally, giving a concrete signal for when it's actually safe to advance. See [Memory Context Management](../Investigations/Memory%20Context%20Management.md).

## Related
- [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md)
- [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md)
- [K - Chat Interface](K%20-%20Chat%20Interface.md)
