# Chat Interface (Module K)

The actual surface where you talk to Kathrena (Module G) and hear her talk back. Built on
**Chainlit** - see `Architecture/Modules/K - Chat Interface.md` for the design spec.

Voice input (a push-to-talk hotkey) and voice output (Kokoro text-to-speech + a voice-persona
effects stage) are both wired in - see `Architecture/Decisions Log.md` Rounds 16 and 18. Long-term
memory (Module J) is also wired in - see `Architecture/Decisions Log.md` Round 19.

## Install

Chainlit, `kokoro`, and `pedalboard` are already declared in `pyproject.toml` - if you haven't run
the shared `.venv` setup yet, see `src/kathrena/voice_log/README.md`. Kokoro needs `espeak-ng` on
PATH (Windows: install from https://github.com/espeak-ng/espeak-ng/releases). Needs a running
TextGen server (Module G's LLM backend) and an already-indexed vault (Module F) to be useful - see
those modules' READMEs.

## Configure

Mostly composes other modules' own configs directly (`AgentCoreConfig`, `RagIndexConfig`,
`PushToTalkConfig` - see their own READMEs for settings keys). Set
`common.vault_root` and, if your TextGen server isn't on the default port, `llm_profiles.local`
in `data/settings.yaml` (see `kathrena.llm`).

| Settings key | Default | Purpose |
| --- | --- | --- |
| `chat_interface.voice_output_enabled` | `true` | Set to `false` to skip loading Kokoro/pedalboard entirely and never speak |
| `chat_interface.kokoro_lang_code` / `chat_interface.kokoro_voice` | `a` / `af_heart` | Kokoro language/voice - must be a matching pair |
| `chat_interface.pitch_shift_semitones` | `-2.0` | Voice-persona pitch shift |
| `chat_interface.highpass_cutoff_hz` | `150.0` | Voice-persona highpass cutoff |
| `chat_interface.distortion_drive_db` | `6.0` | Voice-persona distortion amount |
| `chat_interface.chorus_rate_hz` / `chat_interface.chorus_depth` | `1.5` / `0.25` | Voice-persona chorus effect |

The voice-persona defaults are starting points meant to be tuned by ear, not precisely validated
values - see `kathrena.chat_interface.voice_effects`.

## Run

```powershell
.venv\Scripts\chainlit.exe run src/kathrena/chat_interface/app.py -w
```

Edit `data/settings.yaml`'s `common.vault_root` first (see the top-level README's Running section).

Opens at [http://localhost:8000](http://localhost:8000). `-w` auto-reloads on code changes.

- Each browser session gets its own LangGraph conversation thread (`cl.user_session`) - closing
  the tab and starting a new one starts a fresh conversation; the same tab/session keeps its
  history (persisted via `AgentCoreConfig`'s checkpoint DB) across reconnects.
- Each session also starts its own push-to-talk listener (see Module G's README) - hold the
  configured hotkey (default: Scroll Lock) while you speak, then release. It stops when the tab
  closes. Only one tab should have this open at a time - two sessions both trying to use the
  microphone at once isn't supported.
- When a turn came in via push-to-talk, Kathrena's reply is also spoken (Kokoro +
  the voice-persona effects) and attached as an auto-playing audio element. Typed questions get a
  typed (silent) answer.

## Test

There's no dedicated test suite for `app.py` itself - it's a thin wiring layer with no logic of
its own (config composition + Chainlit event handlers that delegate straight to
`kathrena.agent_core.run_turn`, already tested in `tests/agent_core`). Sanity-check it by actually
running it (see Run, above) against a real TextGen server.

## Lint

```powershell
.venv\Scripts\python.exe -m ruff check src/kathrena/chat_interface
```
