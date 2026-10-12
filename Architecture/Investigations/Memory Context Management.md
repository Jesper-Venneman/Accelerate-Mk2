Research/design dump for Further Considerations' "Fix memory system overload" note, written
alongside Decisions Log Round 29 (which made the problem more urgent by letting a thread survive
restarts - see [Chainlit Data Layer](Chainlit%20Data%20Layer.md) and [G - Kathrena Agent Core](../Modules/G%20-%20Kathrena%20Agent%20Core.md)). **Implemented in Round 30**
(137 tests passing) - both Part 1 and the persisted-marker version of Part 2 below, confirmed safe
against LangMem's actual installed source rather than assumed.

## Where "full history, every time" actually happens today
Two independent consumers, both currently unbounded:

1. **The live reply.** `build_agent_graph`'s `call_model`/`call_reply_model` nodes
   (`kathrena/agent_core/graph.py`) build the prompt as `[SystemMessage, *state["messages"]]` -
   the *entire* accumulated conversation, every single turn, no cap. `state["messages"]` uses a
   plain `operator.add` reducer (not LangGraph's `add_messages`), so it's an append-only list for
   the life of the thread.
2. **Background memory extraction.** `run_turn` reads `graph.get_state(run_config).values["messages"]`
   (the same full list) and hands it to `memory_provider.remember(full_history, thread_id)` on
   *every* turn. `LangMemProvider.remember` schedules this via LangMem's `ReflectionExecutor`,
   which debounces (cancels + resubmits) per `thread_id` - only the last submission before the
   conversation goes idle for `reflection_delay_seconds` actually runs - but whichever submission
   does run still carries the *entire* history, not just what's new since the last time
   extraction actually ran.

Before Round 29, growth was naturally capped by session length (a restart always started a fresh
thread). After Round 29, a resumed thread's history can grow forever across every restart too -
so both of these get meaningfully worse over the app's actual intended lifetime ("designed to run
alongside the device constantly," per the original Further Considerations note).

## Part 1: capping the live prompt
**Recommended: `langchain_core.messages.trim_messages`**, applied inside `call_model` and
`call_reply_model` to a copy of `state["messages"]` before it's sent to the model - the
*checkpointed* state (and anything memory-related that reads it) stays untouched; only what the
LLM actually sees each call gets capped.

```python
from langchain_core.messages import trim_messages

trimmed = trim_messages(
    state["messages"],
    strategy="last",
    token_counter=len,       # treats each message as weight 1 - a message-count window, see below
    max_tokens=config.history_window_messages,
    start_on="human",        # never start the window on a dangling ToolMessage/tool-calling AIMessage
)
messages = [SystemMessage(content=system_prompt), *trimmed]
```

- **Message-count window (`token_counter=len`) over a true token-count window:** simpler, and
  avoids needing a tokenizer that's accurate for *both* whichever local model and whichever cloud
  model happen to be in play for a given role (Decisions Log Round 27/28 means the model backing
  any given call can change at runtime) - a real token budget would need per-model tokenizer
  lookup to stay meaningful, which is more moving parts for a first pass. Revisit only if a
  message-count window turns out to not track actual token/context-limit risk closely enough in
  practice.
- **`start_on="human"`** is what makes this safe with tool-calling conversations specifically -
  it trims the window back to the next `HumanMessage` boundary rather than ever starting mid-way
  through an in-progress tool-call exchange (which would leave a dangling `ToolMessage` or an
  `AIMessage` with unanswered `tool_calls`, which most providers reject outright).
- **New config field:** `agent_core.history_window_messages` (`AgentCoreConfig`, `setting_int`,
  sane default e.g. `12`) - a count of messages, not turns (one turn is at least a
  `HumanMessage` + final `AIMessage`, more with tool calls in between).
- Cost: negligible - `trim_messages` is a pure Python pass over an in-memory list already held
  by the graph, no extra I/O or model calls.

## Part 2: capping what background memory extraction re-sends
**Chosen: a persisted per-thread marker**, confirmed safe to implement against LangMem's actual
installed source (not assumed) - see below. The Further Considerations note's own framing - "mark
messages as memorized (possibly with overlap for reinforcement), or a mix of both" - describes
exactly this: a count of how many messages have already been *confirmed* handed to LangMem, so
each `remember()` call only needs to submit the unsent tail (plus a little overlap).

### Advancing the marker at submit time doesn't work
`remember()` gets called on every turn, and LangMem's `ReflectionExecutor` debounces by
cancelling whatever's currently pending for a `thread_id` and replacing it with the new
submission (Decisions Log Round 28's verified finding) - so "submitted" doesn't mean "will run."
If the marker advances the moment `remember()` is *called*, a submission that later gets
cancelled still "counts" as sent even though LangMem never actually saw its messages - the next
submission starts from the new (already-advanced) marker and only re-covers a small `overlap`
window, not the cancelled submission's whole range. Net effect: a chunk of conversation could
silently never reach LangMem at all.

### The fix: advance the marker from a completion callback, not at submit time
Verified directly against LangMem's installed source (`langmem/reflection.py`), not assumed:
`LocalReflectionExecutor.submit()` returns a real `concurrent.futures.Future`. Tracing
`_process_queue`: a submission that gets superseded by a later one for the same `thread_id` has
`.future.cancel()` called on it and resolves as `cancelled()` *without ever invoking the
reflector*; the one submission that actually survives to run resolves normally via
`future.set_result(...)`. That's a concrete, checkable signal - attach
`future.add_done_callback(...)` to the future `submit()` returns, and inside it, only advance the
marker `if not future.cancelled()`. This tells you, after the fact, whether *this exact*
submission's range was truly processed, rather than guessing at submit time. With this fix, the
design no longer loses any range of conversation the way the submit-time version did - every
message eventually gets sent to LangMem by *some* submission, since the marker only ever advances
past messages a submission actually delivered:

```python
def remember(self, messages: list[Any], thread_id: str) -> None:
    self._rebuild_if_needed()
    marker = self._read_marker(thread_id)  # persisted count of messages confirmed sent so far
    to_send = messages[max(0, marker - self._config.memory_marker_overlap_messages):]
    future = self._executor.submit(
        {"messages": to_send},
        config={"configurable": {"thread_id": thread_id}},
        after_seconds=int(self._config.reflection_delay_seconds),
    )
    sent_through = len(messages)  # captured now, used only if this submission actually runs

    def _advance_marker_if_it_actually_ran(f: Any) -> None:
        if not f.cancelled():
            self._write_marker(thread_id, sent_through)

    future.add_done_callback(_advance_marker_if_it_actually_ran)
```

- **Why this is the chosen design, not just the fancier one:** the alternative (trim once the
  untransmitted tail gets too long) permanently drops old, never-yet-extracted material once
  trimmed - fine for a hard safety cap, but a poor fit for "reduce repeated token usage without
  losing anything," which is the actual goal here. The marker design sends each message to
  LangMem exactly once (plus the small deliberate overlap), so persisted long-running
  conversations stop re-paying extraction cost for content already processed, without ever
  giving up on extracting something.
- **Where the marker lives:** the same `SqliteStore` `open_memory_store` already keeps open for
  the process's lifetime (already documented as safe for concurrent/cross-thread access) - a
  small dedicated namespace, e.g. `("memory_markers",)`, keyed by `thread_id`, value
  `{"sent_through": N}`. Persisted (not just in-process state) so it survives a restart - which
  matters now that Round 29 lets a thread's conversation survive restarts too.
- **New `MemoryConfig` field:** `memory_marker_overlap_messages` (small, e.g. `2`) - how many
  already-confirmed messages to re-include for continuity/reinforcement, matching the original
  Further Considerations wording.
- `add_done_callback`'s callback runs on whichever thread resolves the future (LangMem's own
  background worker thread in the normal case) - fine here since all it does is write one small
  persisted value, and `SqliteStore` already serializes its own access internally.
- **Interaction with Module J's existing rebuild-on-profile-change caching (Round 28):** a
  profile switch calls `old_executor.shutdown(wait=False)` on the *old* `ReflectionExecutor`.
  Per `LocalReflectionExecutor.shutdown`'s "drain the queue" phase, any still-queued submission
  gets force-run there regardless of its `cancel_event` - which still resolves its future via
  `set_result(...)` (a genuine, if forced, completion), so the done-callback still fires and the
  marker still advances correctly across a mid-conversation profile switch. Not expected to need
  any special-casing, but worth a real test once this is built, not just an inference.

### Not chosen: trim-when-too-long
Considered and set aside in favor of the marker design above: only trim the payload once the
untransmitted tail grows past a generous threshold, trimming back to a generous cutoff when it
does. Simpler to build (no persisted marker, no callback), but permanently drops very old,
never-yet-extracted material once trimmed rather than guaranteeing it eventually reaches LangMem -
a real loss of information the marker design avoids, and reducing *that* exact repeated-cost
problem without losing anything is the actual goal here. Kept on file in case the marker design
turns out to have an issue in practice and a cheaper fallback is needed:

```python
def remember(self, messages: list[Any], thread_id: str) -> None:
    self._rebuild_if_needed()
    if len(messages) > self._config.memory_trim_threshold_messages:
        messages = messages[-self._config.memory_trim_keep_messages:]
    self._executor.submit(
        {"messages": messages},
        config={"configurable": {"thread_id": thread_id}},
        after_seconds=int(self._config.reflection_delay_seconds),
    )
```

## Interaction between the two parts
Independent and composable - Part 1 only affects what the live model sees per call (checkpointed
state unaffected); Part 2 only affects what `remember()` submits. Implementing one without the
other is safe; recommended to do both together since they fix the same root cause
(unbounded-growth-now-that-threads-persist) at its two actual consumption points.

## Not pursued (for now)
- **Full summarization node** (condense trimmed-off messages into a running summary instead of
  just dropping them) - the more "complete" LangGraph-recipe answer, but requires switching
  `AgentState.messages`'s reducer from `operator.add` to LangGraph's `add_messages` (to use the
  `RemoveMessage` sentinel for actually pruning persisted state) and a new
  summarization LLM call. Meaningfully more moving parts than trimming; revisit only if trimming
  alone turns out to lose context that actually matters in practice - same "prove it's needed
  first" philosophy [J - Memory Module](../Modules/J%20-%20Memory%20Module.md)'s own "Categorization" section already applies to its
  simplified single-namespace memory design.
- **Hard message-count cap with no overlap/marker nuance at all** - simplest possible, but loses
  old material outright with no way to ever recover it, same trade-off as the "not chosen"
  trim-when-too-long option above, just cruder still.

## Related
- [G - Kathrena Agent Core](../Modules/G%20-%20Kathrena%20Agent%20Core.md)
- [J - Memory Module](../Modules/J%20-%20Memory%20Module.md)
- [Chainlit Data Layer](Chainlit%20Data%20Layer.md)
- [Decisions Log](../Decisions%20Log.md) Round 29
- [Further Considerations](../Further%20Considerations.md)
