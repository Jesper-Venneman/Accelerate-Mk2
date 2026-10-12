"""Splits a document's text into embeddable chunks.

Design spec: Architecture/Modules/F - RAG Indexing Module.md
"""

from __future__ import annotations

from kathrena.rag_index.config import RagIndexConfig


def split_document(text: str, config: RagIndexConfig) -> list[str]:
    """Split `text` into overlapping, markdown-aware chunks sized for the embedding model."""
    # Imported lazily so importing this module doesn't require langchain-text-splitters unless used.
    from langchain_text_splitters import MarkdownTextSplitter

    splitter = MarkdownTextSplitter(
        chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap
    )
    return splitter.split_text(text)
