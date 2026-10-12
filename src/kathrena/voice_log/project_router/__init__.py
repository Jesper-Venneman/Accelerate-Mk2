"""Module C: Project Router.

Design spec: Architecture/Modules/C - Project Router Module.md

Matches a transcript to a project via each project's `.md` frontmatter
`synonyms:` list, routing it to a Project Log, Unsorted Log, or Vocal Journal
(see Architecture/Log Types/).
"""

from kathrena.voice_log.project_router.router import LogType, RouteResult, build_synonym_map, route

__all__ = ["LogType", "RouteResult", "build_synonym_map", "route"]
