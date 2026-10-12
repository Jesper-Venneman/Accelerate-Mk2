"""Tests for Module C (kathrena.voice_log.project_router)."""

from __future__ import annotations

from kathrena.voice_log.project_router import LogType, build_synonym_map, route


def _write_project(config, category: str, project_name: str, synonyms: list[str]) -> None:
    project_dir = config.resolve(category) / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    synonym_lines = "\n".join(f"  - {s}" for s in synonyms)
    (project_dir / f"{project_name}.md").write_text(
        f"---\nsynonyms:\n{synonym_lines}\n---\nSome project description.\n",
        encoding="utf-8",
    )


def test_build_synonym_map_includes_edit_to_log(config):
    synonym_map = build_synonym_map(config)

    assert synonym_map["edit to log"] == config.vocal_journal_dir


def test_build_synonym_map_reads_project_synonyms(config):
    _write_project(config, "01 - Projects", "Accelerate", ["Accelerate", "R AI B"])

    synonym_map = build_synonym_map(config)

    assert synonym_map["accelerate"] == config.resolve("01 - Projects") / "Accelerate"
    assert synonym_map["r ai b"] == config.resolve("01 - Projects") / "Accelerate"


def test_build_synonym_map_ignores_project_without_frontmatter(config):
    project_dir = config.resolve("01 - Projects") / "Broken"
    project_dir.mkdir(parents=True)
    (project_dir / "Broken.md").write_text("No frontmatter here.\n", encoding="utf-8")

    synonym_map = build_synonym_map(config)

    assert "broken" not in synonym_map


def test_route_matches_earliest_synonym(config):
    _write_project(config, "01 - Projects", "Accelerate", ["Accelerate"])
    _write_project(config, "01 - Projects", "Blender", ["Blender"])
    synonym_map = build_synonym_map(config)

    result = route("Today for Blender I want to talk about Accelerate too", synonym_map, config)

    assert result.log_type is LogType.PROJECT
    assert result.destination == config.resolve("01 - Projects") / "Blender"


def test_route_falls_back_to_unsorted(config):
    synonym_map = build_synonym_map(config)

    result = route("Just rambling with no project keywords at all", synonym_map, config)

    assert result.log_type is LogType.UNSORTED
    assert result.destination == config.unsorted_logs_dir


def test_route_detects_edit_to_log(config):
    synonym_map = build_synonym_map(config)

    result = route("Edit to log, remember to buy milk", synonym_map, config)

    assert result.log_type is LogType.VOCAL_JOURNAL
    assert result.destination == config.vocal_journal_dir
