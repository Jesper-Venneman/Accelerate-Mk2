"""Plain-text logging of LLM and tool call input/output (Decisions Log Round 32).

Design: Further Considerations' "Log input and output messages for tooling and LLM" note.
Deliberately opt-in per role rather than global: `kathrena.llm.build_chat_model`'s `log_label`
parameter attaches this to a chat model's own config (`.with_config(callbacks=[...])`), so a
caller that doesn't pass a label stays unlogged.

One shared log file for everything, rotated daily at midnight with
the last 10 days kept (`TimedRotatingFileHandler`) - unlimited size within a day.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from kathrena.settings import setting_path

_LOGGER_NAME = "kathrena.llm_calls"


@dataclass(frozen=True)
class LLMLoggingConfig:
    path: Path = field(
        default_factory=lambda: setting_path("llm_logging", "path", "./data/logs/llm_calls.log")
    )


def _get_logger(path: Path) -> logging.Logger:
    """The shared logger, (re)attached to `path` if it isn't already - not just "has any handler
    at all": tests (and a changed `llm_logging.path` setting) use a different path each time, so
    checking the handler's actual target keeps this correct rather than silently stale."""
    from logging.handlers import TimedRotatingFileHandler

    logger = logging.getLogger(_LOGGER_NAME)
    target = str(path.resolve())
    if not any(
        isinstance(h, TimedRotatingFileHandler) and h.baseFilename == target
        for h in logger.handlers
    ):
        logger.handlers.clear()
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = TimedRotatingFileHandler(
            str(path), when="midnight", backupCount=10, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False  # keep this out of Chainlit's own console logging
    return logger


def log_tool_call(
    label: str, tool_name: str, args: dict[str, Any], result: Any, path: Path | None = None
) -> None:
    """Log one tool invocation's input/output - called directly from `call_tools`, which invokes
    tools itself rather than through a chat model's own callbacks."""
    logger = _get_logger(path or LLMLoggingConfig().path)
    logger.info("[%s] TOOL %s IN: %r", label, tool_name, args)
    logger.info("[%s] TOOL %s OUT: %r", label, tool_name, result)


def with_logging(model: Any, label: str) -> Any:
    """Attach call logging to `model` - call this *last*, after `.bind_tools()`/any other
    composition.
    """
    return model.with_config(callbacks=[LoggingCallbackHandler(label)])


class LoggingCallbackHandler(BaseCallbackHandler):
    """Logs a chat model's full input messages and output - attach via `with_logging(model,
    label)` below.
    """

    def __init__(self, label: str, path: Path | None = None) -> None:
        self._label = label
        self._logger = _get_logger(path or LLMLoggingConfig().path)

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        for batch in messages:
            rendered = " | ".join(f"{m.type}: {m.content!r}" for m in batch)
            self._logger.info("[%s] LLM IN: %s", self._label, rendered)

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        for generations in response.generations:
            for generation in generations:
                # When the model makes a tool call instead of replying with text, .text is
                # blank - the real output is in the message's tool_calls, not content.
                tool_calls = getattr(getattr(generation, "message", None), "tool_calls", None)
                if tool_calls:
                    rendered = ", ".join(f"{c['name']}({c['args']!r})" for c in tool_calls)
                    self._logger.info(
                        "[%s] LLM OUT: %r (tool_calls: %s)", self._label, generation.text, rendered
                    )
                else:
                    self._logger.info("[%s] LLM OUT: %r", self._label, generation.text)
