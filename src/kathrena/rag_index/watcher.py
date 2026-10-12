"""Watches the vault for changes and keeps the vector store in sync.

Design spec: Architecture/Modules/F - RAG Indexing Module.md

Complements `run_full_index` (the resumable bulk pass): once the vault is fully indexed, this
watcher keeps it that way by re-indexing (or removing) a single file whenever it changes, without
the overhead of a full LangGraph run for a one-file update.

Debounced per file: Obsidian saves to disk on every keystroke, so reindexing on every raw
`on_modified` event would re-embed a file dozens of times while it's still being edited. Each
change (re)starts a `config.watch_quiet_period_seconds` timer for that file; only once no further
change arrives within that window does it actually get indexed, so a burst of edits collapses into
one reindex of the final content.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from kathrena.rag_index.config import RagIndexConfig
from kathrena.rag_index.indexer import index_one
from kathrena.rag_index.opt_out import OptOutChecker
from kathrena.rag_index.vector_store import VectorStore


class VaultWatcher:
    """Watches `config.vault_root` for markdown changes and keeps `store` up to date."""

    def __init__(self, config: RagIndexConfig, store: VectorStore) -> None:
        self._config = config
        self._store = store
        self._opt_out = OptOutChecker(config.vault_root, config.rag_index_frontmatter_key)
        self._observer = Observer()
        self._lock = threading.Lock()
        self._pending: dict[Path, threading.Timer] = {}

    def start(self) -> None:
        """Begin watching for vault changes. Runs on a background thread until `stop()`."""
        handler = _Handler(
            self._config, self._opt_out, self._schedule_reindex, self._cancel_and_delete
        )
        self._observer.schedule(handler, str(self._config.vault_root), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        with self._lock:
            for timer in self._pending.values():
                timer.cancel()
            self._pending.clear()
        self._observer.stop()
        self._observer.join()

    def _schedule_reindex(self, path: Path) -> None:
        """(Re)start `path`'s quiet-period timer - a new change resets the clock."""
        with self._lock:
            existing = self._pending.pop(path, None)
            if existing is not None:
                existing.cancel()
            timer = threading.Timer(
                self._config.watch_quiet_period_seconds, self._run_reindex, args=(path,)
            )
            timer.daemon = True
            self._pending[path] = timer
            timer.start()

    def _run_reindex(self, path: Path) -> None:
        with self._lock:
            self._pending.pop(path, None)
        if path.exists():  # may have been deleted/moved during the quiet period
            index_one(self._config, self._store, path)

    def _cancel_and_delete(self, path: Path) -> None:
        with self._lock:
            existing = self._pending.pop(path, None)
            if existing is not None:
                existing.cancel()
        self._store.delete(doc_id=str(path.relative_to(self._config.vault_root)))


class _Handler(FileSystemEventHandler):
    """Filters raw filesystem events down to relevant markdown changes, then delegates.

    Doesn't touch `VectorStore` directly - `on_change`/`on_delete` are `VaultWatcher`'s debounce
    scheduler, so this class only needs to know *what* changed, not *when* to act on it.
    """

    def __init__(
        self,
        config: RagIndexConfig,
        opt_out: OptOutChecker,
        on_change: Callable[[Path], None],
        on_delete: Callable[[Path], None],
    ) -> None:
        self._config = config
        self._opt_out = opt_out
        self._on_change = on_change
        self._on_delete = on_delete

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle_change(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle_change(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix == ".md":
            self._on_delete(path)

    def _handle_change(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix != ".md" or self._opt_out.is_opted_out(path):
            return
        relative_parts = path.relative_to(self._config.vault_root).parts
        if any(part in self._config.exclude_dir_names for part in relative_parts):
            return
        self._on_change(path)
