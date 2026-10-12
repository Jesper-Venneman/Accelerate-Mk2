# Voice Log Pipeline (Modules A-E)

Watches for new voice-log recordings, transcribes them, routes them to the right project,
refines/summarizes them, and writes the result into the vault. Independent of the Kathrena
AI-agent side (Modules F-K) - see `Architecture/Architecture Overview.md` for the full picture
and `Architecture/Modules/` for each module's spec.

## Install

From the repo root:

```powershell
.\scripts\setup-venv.ps1
```

This creates `.venv`, installs the CUDA build of `torch` (adjust the index via
`-CudaIndex cu1xx`, or pass `-CudaIndex cpu` if you don't have an NVIDIA GPU), then installs the
rest of the project. Doing this in two ordered pip installs matters - see `pyproject.toml`'s
`torch` comment and `Architecture/Decisions Log.md` Round 15 for why a single `pip install -e
".[dev]"` alone would silently give you the CPU-only build instead.

## Configure

Everything has a default (see `src/kathrena/config.py`), but you'll almost always want to at
least set the vault path. Common overrides, in `data/settings.yaml`:

| Settings key | Default | Purpose |
| --- | --- | --- |
| `common.vault_root` | `.` | Path to your Obsidian vault |
| `pipeline.llm_profile` | `local` | Which named `llm_profiles` entry (see `kathrena.llm`) Module E's refiner is built from |
| `pipeline.whisper_model_size` | `medium` | Whisper model size |
| `pipeline.whisper_device` | `cuda` | `cuda` or `cpu` |

## Run

```powershell
.venv\Scripts\python.exe -m kathrena.voice_log.pipeline
```

Edit `data/settings.yaml`'s `common.vault_root` first (see the top-level README's Running section).

Watches `91 - Resources/81 - logs/Unprocessed logs` in the vault for `VoiceLog_*.wav` files,
processes each one, and moves it to the `Processed logs` folder when done. `Ctrl+C` to stop.

## Test

```powershell
.venv\Scripts\python.exe -m pytest tests/voice_log -q
```

## Lint

```powershell
.venv\Scripts\python.exe -m ruff check src/kathrena/voice_log tests/voice_log
```
