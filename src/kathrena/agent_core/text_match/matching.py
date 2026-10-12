"""Punctuation/whitespace-tolerant substring search.

Design spec: Architecture/Modules/G - Kathrena Agent Core.md
Decision: Architecture/Decisions Log.md, Round 24.
"""

from __future__ import annotations

import re

_NOT_WORD_OR_SPACE_RE = re.compile(r"[^\w\s]")


def _normalize_with_offsets(text: str) -> tuple[str, list[int]]:
    """Lowercase `text`, drop punctuation, and collapse whitespace runs to a single space, while
    recording each kept character's original index - lets a match found in the normalized string
    be mapped back to a span in the original text."""
    normalized_chars: list[str] = []
    offsets: list[int] = []
    previous_was_space = False
    for index, char in enumerate(text):
        if _NOT_WORD_OR_SPACE_RE.match(char):
            continue
        if char.isspace():
            if previous_was_space:
                continue
            char = " "
            previous_was_space = True
        else:
            previous_was_space = False
        normalized_chars.append(char.lower())
        offsets.append(index)
    return "".join(normalized_chars), offsets


def find_span(text: str, near_text: str) -> tuple[int, int] | None:
    """Find `near_text` inside `text`, tolerant of punctuation/whitespace differences between the
    two (e.g. a chunk re-typed or copied with different quoting/line breaks). Returns the matching
    `(start, end)` span in `text`'s own original indices, or None if no match is found."""
    normalized_text, offsets = _normalize_with_offsets(text)
    normalized_near, _ = _normalize_with_offsets(near_text)
    if not normalized_near:
        return None
    match_index = normalized_text.find(normalized_near)
    if match_index == -1:
        return None
    start = offsets[match_index]
    end = offsets[match_index + len(normalized_near) - 1] + 1
    return start, end
