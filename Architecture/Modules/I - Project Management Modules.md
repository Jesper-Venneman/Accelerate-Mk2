Four active, independently-maintainable modules that read from [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md) and write through [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md).

Orchestrated with LangGraph, same as [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md) and [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md), so proposing a change is just calling into the shared approval-gate graph.

Deeper specs beyond the skill/sub-agent split below are intentionally deferred until [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md) and [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md) are built and evaluated - see [Decisions Log](../Decisions%20Log.md).

## Implementation pattern: skill vs. sub-agent
Each module is either a **skill** (a bound tool [Kathrena](G%20-%20Kathrena%20Agent%20Core.md) calls directly within a live conversation turn - single-shot, no independent reasoning loop) or a **sub-agent** (its own small LangGraph subgraph running autonomously, often in the background, the same pattern as [J - Memory Module](J%20-%20Memory%20Module.md)'s memory-formation agent):
- **I2** - skill: a read-only aggregation tool, no multi-step reasoning needed.
- **I3** - skill for this pass (Decisions Log Round 20): a read-only `list_deadlines` tool, called on-demand rather than run proactively in the background as originally sketched here.
- **I4** - sub-agent: multi-step (read a log, decide what changed, draft a diff, submit through [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md)) - too much reasoning for a single tool call.
- **I5** - skill: a natural-language RAG query tool over [F - RAG Indexing Module](F%20-%20RAG%20Indexing%20Module.md) and [J - Memory Module](J%20-%20Memory%20Module.md), single-shot request/response.

## I2 - Cross-Project Status Dashboard
One view of all active projects.

## I3 - Deadlines/Reminders
**Built, simplified (Decisions Log Round 20):** ships as an on-demand skill (`list_deadlines`),
not the proactive background sub-agent originally sketched below - Kathrena checks when asked
(e.g. "what's due soon?") rather than surfacing things unprompted. Due dates come from a single
`due:` frontmatter field on any vault note - see `kathrena.project_management.deadlines`. Revisit
proactive delivery later if the on-demand form proves useful but insufficient.

## I4 - Auto Note Updater
Drafts updates to a project's `.md` file from processed logs, submitted through [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md).

## I5 - Cross-Project Search/Query
Natural-language queries spanning multiple projects, exposed through [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md).

## ~~I1 - Task/Checklist Tracker~~ (cut from scope for now)
Parses `- [ ]` items across project notes. Cut from the initial build - bidirectional sync against manual checkbox edits needs a proper design before it's worth building. Revisit later as its own design pass rather than reusing this stub. See [Decisions Log](../Decisions%20Log.md).
