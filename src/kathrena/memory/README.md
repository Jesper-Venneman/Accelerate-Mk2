# Memory (Module J)

Gives Kathrena a persistent, evolving memory that builds up over conversations - separate from the
vault knowledge in Module F's RAG index - so she learns about you over time instead of only
retrieving vault content. See `Architecture/Modules/J - Memory Module.md` for the full design spec
and `Architecture/Decisions Log.md` Round 19 for why this module looks the way it does.

For this pass, memories are unstructured/schema-less documents in a single fixed namespace - the
fuller Profile/Collection/Episodic taxonomy from earlier design rounds is deferred to a later pass.
`remember()` caps what it re-submits per thread via a persisted marker rather than resending the
entire conversation every time (Decisions Log Round 30).

## Install

No new dependencies - built on `langgraph.store.sqlite.SqliteStore`, already available via the
`langgraph-checkpoint-sqlite` dependency used by Modules G/H, plus `langmem` (already declared in
`pyproject.toml`). Embeddings reuse the same `sentence-transformers`/`torch` setup as Module F - see
`src/kathrena/voice_log/README.md`'s Install section if you haven't run `setup-venv.ps1` yet.

## Configure

Everything has a default (see `src/kathrena/memory/config.py`). Common overrides, in
`data/settings.yaml`:

| Settings key | Default | Purpose |
| --- | --- | --- |
| `memory.store_path` | `./data/memory.sqlite` | Where the memory `SqliteStore` is persisted |
| `memory.embedding_model_name` | `BAAI/bge-small-en-v1.5` | Hugging Face embedding model (same as Module F, separate instance/database) |
| `memory.embedding_dims` | `384` | Must match the embedding model's actual output size - `SqliteStore` can't infer this |
| `memory.search_limit` | `5` | Max memories returned per `search_memory` recall |
| `memory.reflection_delay_seconds` | `360` | How long a conversation must go idle before background memory extraction runs |
| `memory.llm_profile` | `local` | Which named `llm_profiles` entry (see `kathrena.llm`) background memory extraction is built from - independent from Module G's own choice |
| `memory.marker_overlap_messages` | `2` | How many already-confirmed-sent messages `remember()` re-includes ahead of a thread's marker for continuity (Decisions Log Round 30) |
## Usage

`open_memory_store(config)` opens the `SqliteStore` (kept open for the process's lifetime - it's
internally thread-safe, so don't close/reopen per-call). Wrap it in `LangMemProvider(config, store)`
to get a `MemoryProvider` (the `recall(query)` / `search_memory` and `remember(messages, thread_id)`
Protocol Module G depends on). Pass the provider into `build_agent_graph`/`run_turn` as
`memory_provider=...`; if omitted (`None`), Kathrena has no `search_memory` tool and nothing is
remembered - existing callers are unaffected. See `src/kathrena/chat_interface/app.py` for how it's
wired into the running app.

## Test

```powershell
.venv\Scripts\python.exe -m pytest tests/agent_core -q
```

Memory-related tests live under `tests/agent_core` (a `FakeMemoryProvider` fixture, plus tests for
`build_search_memory_tool` and the `memory_provider` wiring in `run_turn`), matching how Module F's
`FakeVectorStore` is tested from Module G's side rather than in a dedicated `tests/memory` suite -
this module has no non-trivial standalone logic of its own beyond thin wrappers around
`SqliteStore`/LangMem, which were validated with real ad-hoc smoke tests instead (put/search
returns correctly ranked results; confirmed embedding dimensions).

## Lint

```powershell
.venv\Scripts\python.exe -m ruff check src/kathrena/memory
```
