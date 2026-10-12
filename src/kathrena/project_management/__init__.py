"""Module I: Project Management Modules.

Design spec: Architecture/Modules/I - Project Management Modules.md

Four independent skill/sub-agent modules (I2-I5) reading from
`kathrena.rag_index` (Module F) and writing through `kathrena.approval_gate`
(Module H). Deeper specs deliberately deferred until Modules F/G are built and
evaluated - see the Decisions Log (Round 12).

I3 (deadlines/reminders) is the first one built: an on-demand `list_deadlines`
skill rather than the proactive background sub-agent originally sketched -
see Decisions Log Round 20.
"""

from kathrena.project_management.config import ProjectManagementConfig
from kathrena.project_management.deadlines import Deadline, list_upcoming_deadlines

__all__ = ["Deadline", "ProjectManagementConfig", "list_upcoming_deadlines"]
