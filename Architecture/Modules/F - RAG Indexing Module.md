Keeps a searchable, up-to-date index of the vault for [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md) and the [I - Project Management Modules](I%20-%20Project%20Management%20Modules.md).

## Responsibilities
- Watch the whole vault for changes, chunk + embed changed files, update a local vector store.
- Support a per-project opt-out via a `rag-index: false` frontmatter flag next to `synonyms:` (confirmed, see [Decisions Log](../Decisions%20Log.md)).

## Implementation approach
Uses LangChain's components (text splitters, embeddings interface, vector store integration) for the chunk/embed/upsert/retrieve plumbing - LangGraph has no RAG tooling of its own, it's purely an orchestration layer. The indexing run itself is orchestrated as a LangGraph graph, the same framework backing [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md), [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md), and [I - Project Management Modules](I%20-%20Project%20Management%20Modules.md), so a large or interrupted re-index can resume from its last checkpoint instead of restarting.

Vector store: **Chroma** (embedded, no server process). Embedding model: **BAAI/bge-small-en-v1.5** (local via `sentence-transformers`). Both free/local, no paid tiers - see [Decisions Log](../Decisions%20Log.md).

## Fallback options
If Chroma or bge-small-en-v1.5 don't work out (performance, storage limits, or a future local LLM runtime choice that changes the calculus), these were the other free/local candidates considered:
- **Vector store:** LanceDB (embedded, columnar Lance/Arrow format, more headroom for a very large vault) or Qdrant (free self-hosted, but normally runs as a separate server/Docker container instead of embedded).
- **Embedding model:** nomic-embed-text (Apache-2.0, servable directly via Ollama - worth revisiting if the local LLM runtime ends up being Ollama too) or all-MiniLM-L6-v2 (Apache-2.0, lightest/fastest, slightly lower quality than bge-small).
All of these remain free/local with no paid tiers.

## Related
- [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md)
- [I - Project Management Modules](I%20-%20Project%20Management%20Modules.md)
