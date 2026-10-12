"""Voice-log pipeline (Modules A-E) - separate from the Kathrena AI-agent side (F-K).

Design spec: Architecture/Architecture Overview.md (voice-log pipeline, A-E)

Watches for new voice-log recordings, transcribes, routes, refines, and writes them
into the vault. Doesn't depend on anything in `kathrena.rag_index`/`agent_core`/etc. -
the vault file is the only thing the two halves share, per the architecture split.
"""
