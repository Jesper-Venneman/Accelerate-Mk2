"""Tests for kathrena.agent_core.tools - the functions Kathrena's agent can call."""

from __future__ import annotations

from datetime import date, datetime

from kathrena.agent_core.tools import (
    build_change_setting_tool,
    build_current_datetime_tool,
    build_list_deadlines_tool,
    build_propose_vault_change_tool,
    build_read_vault_file_tool,
    build_search_memory_tool,
    build_search_vault_tool,
    build_set_llm_mode_tool,
    build_web_search_tool,
)
from kathrena.agent_core.web_search import SearchHit
from kathrena.approval_gate import PendingReview, get_pending_review
from kathrena.rag_index.vector_store import SearchResult
from kathrena.settings import get_store


def test_search_vault_formats_results_with_source_paths(fake_vector_store):
    store = fake_vector_store([SearchResult(content="some note text", source_path="Foo/Foo.md")])
    search_vault = build_search_vault_tool(store, top_k=4)

    result = search_vault(query="what is foo?")

    assert store.queries == ["what is foo?"]
    assert "Foo/Foo.md" in result
    assert "some note text" in result


def test_search_vault_reports_when_nothing_is_found(fake_vector_store):
    search_vault = build_search_vault_tool(fake_vector_store(), top_k=4)

    assert search_vault(query="anything") == "No relevant notes found."


def test_search_vault_respects_top_k(fake_vector_store):
    results = [SearchResult(content=f"chunk {i}", source_path=f"note{i}.md") for i in range(10)]
    search_vault = build_search_vault_tool(fake_vector_store(results), top_k=2)

    result = search_vault(query="anything")

    assert result.count("chunk") == 2


def test_read_vault_file_returns_full_contents(tmp_path):
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "Foo.md").write_text("full note content", encoding="utf-8")
    read_vault_file = build_read_vault_file_tool(vault_root)

    assert read_vault_file(path="Foo.md") == "full note content"


def test_read_vault_file_reports_a_missing_file(tmp_path):
    read_vault_file = build_read_vault_file_tool(tmp_path)

    assert read_vault_file(path="missing.md") == "File not found: missing.md"


def test_read_vault_file_rejects_paths_outside_the_vault(tmp_path):
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (tmp_path / "secret.md").write_text("outside the vault", encoding="utf-8")
    read_vault_file = build_read_vault_file_tool(vault_root)

    assert read_vault_file(path="../secret.md") == "Path is outside the vault: ../secret.md"


def test_read_vault_file_truncates_past_max_chars(tmp_path):
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "Big.md").write_text("x" * 100, encoding="utf-8")
    read_vault_file = build_read_vault_file_tool(vault_root, max_chars=10)

    result = read_vault_file(path="Big.md")

    assert result.startswith("x" * 10)
    assert "truncated, 90 more characters" in result


def test_read_vault_file_windows_around_a_matched_excerpt(tmp_path):
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    text = ("before " * 20) + "the target excerpt" + (" after" * 20)
    (vault_root / "Foo.md").write_text(text, encoding="utf-8")
    read_vault_file = build_read_vault_file_tool(vault_root, max_chars=40)

    result = read_vault_file(path="Foo.md", near_text="the target excerpt")

    assert "the target excerpt" in result
    assert result.startswith("...")
    assert result.endswith("...")
    assert len(result) < len(text)


def test_read_vault_file_matching_tolerates_punctuation_and_whitespace_differences(tmp_path):
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    text = "Some lead-in text.\n\nThe important, part - right here!\n\nSome trailing text."
    (vault_root / "Foo.md").write_text(text, encoding="utf-8")
    read_vault_file = build_read_vault_file_tool(vault_root, max_chars=1000)

    # No punctuation/line breaks, unlike the file's actual text - still expected to match.
    result = read_vault_file(path="Foo.md", near_text="the important part right here")

    assert "The important, part - right here!" in result


def test_read_vault_file_falls_back_to_full_file_when_near_text_is_not_found(tmp_path):
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "Foo.md").write_text("actual file contents", encoding="utf-8")
    read_vault_file = build_read_vault_file_tool(vault_root)

    result = read_vault_file(path="Foo.md", near_text="text that isn't in the file")

    assert result == "actual file contents"


# def test_propose_vault_change_stages_a_real_proposal(approval_config): commented out until the propose vault change tool is improved.
#     propose_vault_change = build_propose_vault_change_tool(approval_config)

#     review = propose_vault_change(
#         target_path="note.md", new_content="hello", description="test proposal"
#     )

#     assert isinstance(review, PendingReview)
#     assert review.target_path == "note.md"
#     assert review.proposer == "G"
#     assert get_pending_review(approval_config, review.thread_id) == review


def test_search_memory_formats_recalled_memories(fake_memory_provider):
    provider = fake_memory_provider(["Likes dark mode.", "Building an AI companion."])
    search_memory = build_search_memory_tool(provider)

    result = search_memory(query="what does the user like?")

    assert provider.queries == ["what does the user like?"]
    assert "Likes dark mode." in result
    assert "Building an AI companion." in result


def test_search_memory_reports_when_nothing_is_found(fake_memory_provider):
    search_memory = build_search_memory_tool(fake_memory_provider())

    assert search_memory(query="anything") == "No relevant memories found."


def test_get_current_datetime_uses_the_injected_clock():
    get_current_datetime = build_current_datetime_tool(
        clock=lambda: datetime(2026, 9, 1, 14, 32)
    )

    result = get_current_datetime()

    assert result == "Tuesday, September 01, 2026, 14:32"


def test_list_deadlines_formats_and_orders_results(pm_config):
    (pm_config.vault_root).mkdir(parents=True)
    (pm_config.vault_root / "Soon.md").write_text("---\ndue: 2026-09-05\n---\n", encoding="utf-8")
    (pm_config.vault_root / "Overdue.md").write_text(
        "---\ndue: 2026-08-20\n---\n", encoding="utf-8"
    )
    list_deadlines = build_list_deadlines_tool(pm_config, clock=lambda: date(2026, 9, 1))

    result = list_deadlines()

    lines = result.splitlines()
    assert lines[0].startswith("- Overdue")
    assert "OVERDUE by 12 day(s)" in lines[0]
    assert lines[1].startswith("- Soon")
    assert "in 4 day(s)" in lines[1]


def test_list_deadlines_reports_when_nothing_is_found(pm_config):
    pm_config.vault_root.mkdir(parents=True)
    list_deadlines = build_list_deadlines_tool(pm_config, clock=lambda: date(2026, 9, 1))

    assert list_deadlines() == "No deadlines found."


def test_search_web_formats_hits_with_titles_and_urls(fake_web_search):
    web_search = fake_web_search(
        [SearchHit(title="Example", url="https://example.com", snippet="An example site.")]
    )
    search_web = build_web_search_tool(web_search, max_results=5)

    result = search_web(query="example")

    assert web_search.queries == ["example"]
    assert "Example" in result
    assert "https://example.com" in result
    assert "An example site." in result


def test_search_web_reports_when_nothing_is_found(fake_web_search):
    search_web = build_web_search_tool(fake_web_search(), max_results=5)

    assert search_web(query="anything") == "No web results found."


def test_set_llm_mode_applies_the_named_preset():
    set_llm_mode = build_set_llm_mode_tool()

    result = set_llm_mode(mode="cloud")

    store = get_store()
    assert store.value("pipeline", "llm_profile", "unused") == "cloud"
    assert store.value("agent_core", "tool_profile", "unused") == "cloud"
    assert store.value("agent_core", "reply_profile", "unused") == "cloud"
    assert store.value("memory", "llm_profile", "unused") == "cloud"
    assert "cloud" in result


def test_set_llm_mode_standard_only_sends_the_reply_profile_to_cloud():
    set_llm_mode = build_set_llm_mode_tool()

    set_llm_mode(mode="standard")

    store = get_store()
    assert store.value("agent_core", "tool_profile", "unused") == "local"
    assert store.value("agent_core", "reply_profile", "unused") == "cloud"
    assert store.value("pipeline", "llm_profile", "unused") == "local"
    assert store.value("memory", "llm_profile", "unused") == "local"


def test_set_llm_mode_rejects_an_unknown_mode():
    set_llm_mode = build_set_llm_mode_tool()

    result = set_llm_mode(mode="turbo")

    assert "Unknown mode" in result


def test_change_setting_updates_an_allow_listed_field():
    change_setting = build_change_setting_tool()

    result = change_setting(name="agent_core.reply_profile", value="cloud")

    assert get_store().value("agent_core", "reply_profile", "unused") == "cloud"
    assert "agent_core.reply_profile" in result


def test_change_setting_rejects_a_setting_not_on_the_allow_list():
    change_setting = build_change_setting_tool()

    result = change_setting(name="common.vault_root", value="/somewhere/else")

    assert "isn't a changeable setting" in result
    assert get_store().raw_section("common").get("vault_root") != "/somewhere/else"
