"""Command-line entry point for the RAG index: `python -m kathrena.rag_index`.

Design spec: Architecture/Modules/F - RAG Indexing Module.md

Mirrors `kathrena.voice_log.pipeline`'s `python -m` entry point so both halves of the project
are runnable the same way: a resumable full pass to catch up on anything missed while this
process wasn't running, then an incremental watch that keeps the store in sync from then on.
"""

from __future__ import annotations

import logging
import time

from kathrena.rag_index.config import RagIndexConfig
from kathrena.rag_index.indexer import run_full_index
from kathrena.rag_index.vector_store import ChromaVectorStore
from kathrena.rag_index.watcher import VaultWatcher
from kathrena.settings import SettingsNotConfiguredError, ensure_configured


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        ensure_configured()
    except SettingsNotConfiguredError as exc:
        raise SystemExit(str(exc)) from exc
    config = RagIndexConfig()
    store = ChromaVectorStore(config)

    logging.info("Indexing %s into Chroma collection %r", config.vault_root, config.collection_name)
    indexed_count = run_full_index(config, store)
    logging.info("Initial index done: %d file(s) into %s", indexed_count, config.persist_directory)

    watcher = VaultWatcher(config, store)
    watcher.start()
    logging.info("Watching %s for changes... (Ctrl+C to stop)", config.vault_root)
    try:
        while True:
            time.sleep(1)  # watchdog's Observer runs on its own thread; keep the process alive.
    except KeyboardInterrupt:
        watcher.stop()


if __name__ == "__main__":
    main()

