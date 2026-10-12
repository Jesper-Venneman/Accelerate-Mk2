# RAG Indexing (Module F)

Indexes the Obsidian vault into a local Chroma vector store for Kathrena's RAG retrieval, with
resumable full-vault indexing and incremental reindex-on-change. Independent of the voice-log
pipeline (Modules A-E) - see `Architecture/Architecture Overview.md` for the full picture and
`Architecture/Modules/F - RAG Indexing Module.md` for the design spec.

## Install

Uses the same `.venv` and `torch` install as the voice-log pipeline - if you've already set that
up (see `src/kathrena/voice_log/README.md`), nothing extra is needed for CUDA. Embeddings run via
`sentence-transformers`, which uses whatever `torch` build is already installed (GPU if available,
CPU otherwise) - there's no separate CUDA index-url step for this module.

From the repo root, a fresh setup is just:

```powershell
.\scripts\setup-venv.ps1
```

See `src/kathrena/voice_log/README.md`'s Install section for what this does and why the CUDA
torch install has to happen before the rest of the project.

## Configure

Everything has a default (see `src/kathrena/rag_index/config.py`), but you'll almost always want
to at least set the vault path. Common overrides, in `data/settings.yaml`:

| Settings key | Default | Purpose |
| --- | --- | --- |
| `common.vault_root` | `.` | Path to your Obsidian vault |
| `rag_index.persist_directory` | `./chroma` | Where the Chroma server persists its data - passed to `chroma run --path` |
| `rag_index.chroma_host` / `rag_index.chroma_port` | `127.0.0.1` / `8601` | Where the Chroma server (a sibling process, see `start.ps1`) is listening |
| `rag_index.chroma_connect_retries` / `rag_index.chroma_connect_retry_delay_seconds` | `10` / `1.0` | How long to keep retrying the connection if the server hasn't finished starting yet |
| `rag_index.checkpoint_path` | `./data/rag_index_checkpoints.sqlite` | LangGraph checkpoint DB, enables resuming an interrupted full index |
| `rag_index.collection_name` | `vault` | Chroma collection name |
| `rag_index.embedding_model_name` | `BAAI/bge-small-en-v1.5` | Hugging Face embedding model (downloaded on first use) |
| `rag_index.chunk_size` / `rag_index.chunk_overlap` | `1000` / `150` | Markdown chunking size/overlap |
| `rag_index.watch_quiet_period_seconds` | `30` (seconds) | How long a file must go unedited before the watcher reindexes it |

A file/folder can opt out of indexing by setting `rag-index: false` in its own or its project
folder's frontmatter (`{Folder}/{Folder}.md`) - opting out a project folder opts out everything
nested under it.

## Run

Needs a Chroma server running first (`start.ps1` does this for you - see the top-level README):

```powershell
.venv\Scripts\chroma.exe run --path ./chroma --host 127.0.0.1 --port 8601
```

Then, in another terminal:

```powershell
.venv\Scripts\python.exe -m kathrena.rag_index
```

Edit `data/settings.yaml`'s `common.vault_root` first (see the top-level README's Running section).

Runs a resumable full index first (safe to re-run; picks up where a previous run left off if it
was interrupted, and catches anything that changed while this process wasn't running), then
starts `VaultWatcher` to keep the store in sync incrementally as files change. `Ctrl+C` to stop.

## Test

```powershell
.venv\Scripts\python.exe -m pytest tests/rag_index -q
```

Tests use a `FakeVectorStore` and don't require `chromadb`/`sentence-transformers` to be
installed - only `langgraph`, `langgraph-checkpoint-sqlite`, and `langchain-text-splitters`.

## Lint

```powershell
.venv\Scripts\python.exe -m ruff check src/kathrena/rag_index tests/rag_index
```
