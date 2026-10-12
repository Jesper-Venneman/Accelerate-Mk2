"""Module D: Log Writer.

Design spec: Architecture/Modules/D - Log Writer Module.md

Writes the final log entry (Project Log, Unsorted Log, or Vocal Journal format)
into the vault, where `kathrena.rag_index` (Module F) picks it up automatically.
"""

from kathrena.voice_log.log_writer.writer import LogEntry, write_log

__all__ = ["LogEntry", "write_log"]
