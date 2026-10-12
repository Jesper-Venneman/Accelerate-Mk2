# Project Management (Module I)

Four independent skill/sub-agent modules (I2-I5) reading from `kathrena.rag_index` (Module F) and
writing through `kathrena.approval_gate` (Module H) - see
`Architecture/Modules/I - Project Management Modules.md` for the full design spec. I1
(task/checklist tracking) is cut from scope (Decisions Log Round 6).

**Built so far: I3 (deadlines/reminders)**, as an on-demand `list_deadlines` skill rather than the
proactive background sub-agent originally sketched - see Decisions Log Round 20. I2, I4, I5 aren't
built yet.

## Install

No new dependencies - `kathrena.project_management.deadlines` only needs `pyyaml`, already in
`pyproject.toml` for `kathrena.rag_index`'s frontmatter parsing.

## Configure

| Settings key | Default | Purpose |
| --- | --- | --- |
| `common.vault_root` | `.` | Path to your Obsidian vault - same key as Module F |
| `project_management.default_within_days` | `30` | Default "close" window for `list_deadlines` when the LLM doesn't say one itself |
| `project_management.due_frontmatter_key` | `due` | Frontmatter key holding a note's due date |

A note gets a deadline by adding a `due:` field to its own frontmatter, e.g.:

```yaml
---
synonyms: [foo]
due: 2026-09-15
---
```

## Usage

```python
from kathrena.project_management import ProjectManagementConfig, list_upcoming_deadlines

config = ProjectManagementConfig()
for deadline in list_upcoming_deadlines(config, within_days=14):
    print(deadline.title, deadline.due_date, deadline.target_path)
```

`kathrena.agent_core.tools.build_list_deadlines_tool` wraps this as the `list_deadlines` tool
bound into Kathrena's agent graph (Module G) whenever a `pm_config` is given to
`run_turn`/`build_agent_graph` - see `src/kathrena/agent_core/README.md`'s Tools section. It's a
skill Kathrena only calls when asked (e.g. "are there any close deadlines?"), never run
proactively on her own.

## Test

```powershell
.venv\Scripts\python.exe -m pytest tests/project_management -q
```

Tests write real temp markdown files with frontmatter and read them back - no vault or LLM needed.

## Lint

```powershell
.venv\Scripts\python.exe -m ruff check src/kathrena/project_management tests/project_management
```
