"""Tests for Module F's chunker (kathrena.rag_index.chunker)."""

from __future__ import annotations

from kathrena.rag_index.chunker import split_document


def test_short_text_is_a_single_chunk(rag_config):
    chunks = split_document("A short note.", rag_config)

    assert chunks == ["A short note."]


def test_long_text_is_split_into_multiple_chunks(rag_config):
    long_text = "\n\n".join(f"Paragraph {i}. " * 20 for i in range(20))

    chunks = split_document(long_text, rag_config)

    assert len(chunks) > 1
    assert all(len(chunk) <= rag_config.chunk_size + rag_config.chunk_overlap for chunk in chunks)
