"""Configuration for Module F (RAG indexing).

Design spec: Architecture/Modules/F - RAG Indexing Module.md

Every value has a sensible default so indexing works against a fresh vault checkout without
configuration, but each can be overridden in `data/settings.yaml`.
Independent from `kathrena.config.PipelineConfig` (the voice-log pipeline's config) - the two
halves only agree on the shared "common" settings section's `vault_root`, nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kathrena.settings import setting_float, setting_int, setting_path, setting_str


@dataclass(frozen=True)
class RagIndexConfig:
    """Vault location, chunking, and vector-store settings for the RAG index."""

    vault_root: Path = field(default_factory=lambda: setting_path("common", "vault_root", "."))

    # Local runtime data (Architecture/Architecture Overview.md#Runtime architecture) - both
    # already covered by .gitignore. Read by the Chroma server process (`chroma run --path ...`,
    # see start.ps1), not by ChromaVectorStore itself (Decisions Log Round 33).
    persist_directory: Path = field(
        default_factory=lambda: setting_path("rag_index", "persist_directory", "./chroma")
    )
    checkpoint_path: Path = field(
        default_factory=lambda: setting_path(
            "rag_index", "checkpoint_path", "./data/rag_index_checkpoints.sqlite"
        )
    )

    # Where the Chroma *server* (a sibling process, see start.ps1) is listening - ChromaVectorStore
    # connects to it over HTTP rather than opening its own embedded client (Decisions Log Round
    # 33), so every process sharing this vault sees the same, live vector index.
    chroma_host: str = field(
        default_factory=lambda: setting_str("rag_index", "chroma_host", "127.0.0.1")
    )
    chroma_port: int = field(default_factory=lambda: setting_int("rag_index", "chroma_port", 8601))
    # The server may still be starting up when a client process races against it (start.ps1 launches
    # all of them at once) - retry briefly rather than failing hard on the first attempt.
    chroma_connect_retries: int = field(
        default_factory=lambda: setting_int("rag_index", "chroma_connect_retries", 10)
    )
    chroma_connect_retry_delay_seconds: float = field(
        default_factory=lambda: setting_float(
            "rag_index", "chroma_connect_retry_delay_seconds", 1.0
        )
    )

    collection_name: str = field(
        default_factory=lambda: setting_str("rag_index", "collection_name", "vault")
    )
    embedding_model_name: str = field(
        default_factory=lambda: setting_str(
            "rag_index", "embedding_model_name", "BAAI/bge-small-en-v1.5"
        )
    )
    chunk_size: int = field(default_factory=lambda: setting_int("rag_index", "chunk_size", 1000))
    chunk_overlap: int = field(
        default_factory=lambda: setting_int("rag_index", "chunk_overlap", 150)
    )

    # Obsidian saves to disk on every keystroke - debounce so a file only gets reindexed once it's
    # been quiet for this long, instead of on every intermediate save while it's being edited.
    watch_quiet_period_seconds: float = field(
        default_factory=lambda: setting_float("rag_index", "watch_quiet_period_seconds", 30.0)
    )

    include_glob: str = "**/*.md"
    exclude_dir_names: tuple[str, ...] = (".obsidian", ".git", ".venv", ".trash")
    rag_index_frontmatter_key: str = "rag-index"
