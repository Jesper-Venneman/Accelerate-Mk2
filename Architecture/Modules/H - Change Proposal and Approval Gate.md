The safety gate: nothing from [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md) or the [I - Project Management Modules](I%20-%20Project%20Management%20Modules.md) touches the vault without your sign-off.

## Responsibilities
- Queue any proposed vault edit as a reviewable diff/draft.
- Only commit after explicit user approval.

## Implementation approach
Built on LangGraph: a proposed vault write calls `interrupt()` inside its node, pausing the graph and surfacing the diff; approving or rejecting resumes it via `Command(resume=...)`. The `SqliteSaver` checkpointer persists paused runs to disk, so a proposal survives a service restart and can be approved whenever you get to it - hours or days later.

Design constraint: everything before the `interrupt()` call re-runs on resume, so any side effect ahead of it (e.g. staging the diff) must be idempotent.

## Review UI
[K - Chat Interface](K%20-%20Chat%20Interface.md) for v1 - proposals surface as `cl.Action` approve/reject/edit buttons in the same Chainlit conversation you already have with [Kathrena](G%20-%20Kathrena%20Agent%20Core.md), no extra API needed. A dedicated Obsidian plugin (custom `ItemView` panel, backed by a small local HTTP API from the Python service) is a planned phase-2 enhancement, not part of the initial build.

## Related
- [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md)
- [I - Project Management Modules](I%20-%20Project%20Management%20Modules.md)
