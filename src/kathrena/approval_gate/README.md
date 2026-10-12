# Change Proposal and Approval Gate (Module H)

The safety gate: nothing from Module G (Kathrena Agent Core) or Module I (Project Management
Modules) touches the vault without explicit sign-off. Built on LangGraph's
`interrupt()`/`Command(resume=...)` - a proposed write pauses the graph and persists via a
`SqliteSaver` checkpointer, so it survives a restart and can be approved whenever you get to it,
hours or days later. See
`Architecture/Modules/H - Change Proposal and Approval Gate.md` for the design spec.

## Install

No new dependencies beyond what's already in `pyproject.toml` (`langgraph`,
`langgraph-checkpoint-sqlite`). If you haven't set up the `.venv` yet, see
`src/kathrena/voice_log/README.md`'s Install section.

## Configure

| Settings key | Default | Purpose |
| --- | --- | --- |
| `common.vault_root` | `.` | Path to your Obsidian vault |
| `approval_gate.checkpoint_path` | `./data/approval_gate_checkpoints.sqlite` | LangGraph checkpoint DB - lets a paused proposal be resolved later, even after a restart |

## Usage

This module is a plain Python API, not a standalone process - `kathrena.agent_core` (Module G)
and the Module I sub-agents call into it directly whenever they want to write to the vault:

```python
from kathrena.approval_gate import ApprovalGateConfig, ChangeProposal, Decision, Resolution
from kathrena.approval_gate import propose_change, resolve_change

config = ApprovalGateConfig()
review = propose_change(config, ChangeProposal(
    target_path="Projects/Foo/Foo.md",
    new_content="...",
    description="Summarized this week's logs into the project note",
    proposer="I4",
))
# show review.diff to the user (via Module K)...
outcome = resolve_change(config, review.thread_id, Resolution(Decision.APPROVE))
```

`propose_change` never writes anything by itself - it only pauses and returns a `PendingReview`
(diff + description) for a human to look at. Only `resolve_change` with `Decision.APPROVE` or
`Decision.EDIT` actually writes; `Decision.REJECT` discards it. `get_pending_review` looks up a
paused proposal (e.g. to redisplay it) without resolving it.

## Manually testing against a safe sandbox (not the real vault)

Since this module is the one thing in the project that actually writes into a vault, there's a
small interactive CLI that operates on a throwaway sandbox vault under
`./data/approval_gate_sandbox` - it never reads `common.vault_root`, so there's no way to
accidentally point it at your real notes:

```powershell
.venv\Scripts\python.exe -m kathrena.approval_gate propose demo-note "Hello from a proposal"
# ... note the printed thread_id ...
.venv\Scripts\python.exe -m kathrena.approval_gate resolve <thread_id> approve
Get-Content .\data\approval_gate_sandbox\vault\demo-note.md
```

Try `reject` and `edit <thread_id> edit "different content"` too, and re-run `propose` for the
same note name afterwards to see a real edit diff instead of a "new file" one. Because
`propose`/`resolve` are separate process invocations here, this also demonstrates the actual
persistence guarantee - the paused proposal really is read back from the checkpoint DB, not kept
in memory.

## Test

```powershell
.venv\Scripts\python.exe -m pytest tests/approval_gate -q
```

Every test runs against a `tmp_path`-rooted `ApprovalGateConfig` - fully isolated from any real
vault, same pattern as `tests/rag_index`.

## Lint

```powershell
.venv\Scripts\python.exe -m ruff check src/kathrena/approval_gate tests/approval_gate
```
