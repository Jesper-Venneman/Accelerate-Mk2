"""Tests for kathrena.project_management.deadlines - Module I's I3 skill."""

from __future__ import annotations

from datetime import date

from kathrena.project_management.deadlines import list_upcoming_deadlines


def _write_note(vault_root, relative_path: str, *, due: str | None = None, body: str = "") -> None:
    path = vault_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = f"---\ndue: {due}\n---\n" if due is not None else ""
    path.write_text(f"{frontmatter}{body}", encoding="utf-8")


def test_notes_without_a_due_date_are_ignored(pm_config):
    _write_note(pm_config.vault_root, "no-date.md", body="Just some notes.")

    assert list_upcoming_deadlines(pm_config) == []


def test_finds_notes_with_a_due_date_sorted_soonest_first(pm_config):
    _write_note(pm_config.vault_root, "Later.md", due="2026-09-20")
    _write_note(pm_config.vault_root, "Sooner.md", due="2026-09-05")

    deadlines = list_upcoming_deadlines(pm_config, today=date(2026, 9, 1))

    assert [d.title for d in deadlines] == ["Sooner", "Later"]
    assert deadlines[0].due_date == date(2026, 9, 5)
    assert deadlines[0].target_path == "Sooner.md"


def test_quoted_and_unquoted_yaml_dates_both_parse(pm_config):
    _write_note(pm_config.vault_root, "Quoted.md", due='"2026-09-10"')
    _write_note(pm_config.vault_root, "Unquoted.md", due="2026-09-11")

    deadlines = list_upcoming_deadlines(pm_config, today=date(2026, 9, 1))

    assert {d.due_date for d in deadlines} == {date(2026, 9, 10), date(2026, 9, 11)}


def test_within_days_filters_out_distant_deadlines(pm_config):
    _write_note(pm_config.vault_root, "Close.md", due="2026-09-03")
    _write_note(pm_config.vault_root, "Far.md", due="2026-12-25")

    deadlines = list_upcoming_deadlines(pm_config, within_days=7, today=date(2026, 9, 1))

    assert [d.title for d in deadlines] == ["Close"]


def test_overdue_deadlines_are_always_included_within_a_narrow_window(pm_config):
    _write_note(pm_config.vault_root, "Overdue.md", due="2026-08-01")

    deadlines = list_upcoming_deadlines(pm_config, within_days=1, today=date(2026, 9, 1))

    assert [d.title for d in deadlines] == ["Overdue"]


def test_unparseable_due_value_is_ignored_not_an_error(pm_config):
    _write_note(pm_config.vault_root, "Bad.md", due="not-a-date")

    assert list_upcoming_deadlines(pm_config) == []
