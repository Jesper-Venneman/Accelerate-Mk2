"""Startup gate: refuses to run against an unconfigured vault.

Design spec: Architecture/Architecture Overview.md#Runtime architecture
Decision: Architecture/Decisions Log.md, Round 26.

Because an empty '.' placeholder for the vault will cause the application to start indexing the
wrong directory, `ensure_configured()` is added to closes that gap: on an entry point's first run,
it seeds `data/settings.yaml` with just `common.vault_root` (a placeholder), rather than waiting
for every module's own lazy per-field seeding to slowly populate the file. On every run after
that, it refuses to proceed while `vault_root` is still that placeholder.
After that point, if the vault is set incorrectly by the user, it will be their fault ¯\\_(ツ)_/¯.
"""

from __future__ import annotations

from kathrena.settings.store import get_store

VAULT_ROOT_PLACEHOLDER = "<< SET YOUR VAULT PATH HERE >>" # Not actually here, in the settings.yaml


class SettingsNotConfiguredError(RuntimeError):
    """Raised by `ensure_configured()` when a required setting is still its placeholder."""


def ensure_configured() -> None:
    """Seed `data/settings.yaml`'s required starter field, then refuse to proceed if
    `common.vault_root` hasn't actually been set yet.

    Call this once, before constructing any other module's config, at the top of every real
    entry point - `kathrena.chat_interface.app`, `kathrena.rag_index.__main__`,
    `kathrena.voice_log.pipeline`.
    """
    store = get_store()
    # Verify if the settings file already exists.
    if not store.path.is_file():
        # Create the file with default settings.
        from kathrena.llm import seed_default_profiles

        store.value("common", "vault_root", VAULT_ROOT_PLACEHOLDER)
        seed_default_profiles()
        raise SettingsNotConfiguredError(
                f"Created {store.path} with default settings. Edit its common.vault_root to point at "
                "your Obsidian vault, then restart.")

    # Verify if the vault_root is already set.
    if store.value("common", "vault_root", VAULT_ROOT_PLACEHOLDER) == VAULT_ROOT_PLACEHOLDER:
        raise SettingsNotConfiguredError(
                    f"{store.path}'s common.vault_root is still unset ({VAULT_ROOT_PLACEHOLDER!r}). "
                    "Edit it to point at your Obsidian vault, then restart."
                )
        
