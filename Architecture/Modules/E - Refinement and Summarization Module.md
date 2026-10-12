Cleans up and summarizes the raw transcript before it's written to the log.

## Responsibilities
- Same job as Mk1's `refine_log()` (rewrite/summarize + bullet list of key points), but behind a swappable LLM provider interface.
- Hybrid backend: local by default via **oobabooga's TextGen** (formerly text-generation-webui, already in use, free/AGPL-3.0, 100% offline/private, exposes an OpenAI/Anthropic-compatible API with tool-calling support), cloud API optional per task. Resolved via a named `llm_profiles` entry (`kathrena.llm.resolve_profile`/`build_chat_model`, Decisions Log Round 27) rather than a call of its own - switching this module's profile doesn't affect [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md) or [J - Memory Module](J%20-%20Memory%20Module.md)'s own choice.
- Specific model deliberately left unpinned/swappable - TextGen supports switching backends/models (GGUF, EXL3, Transformers) without restarting, so this isn't a hard dependency.
- Hot-swappable without a restart (Decisions Log Round 28): `LangChainRefiner` remembers which profile it last built its chat model from, and only reconstructs it when a fresh read of `pipeline.llm_profile` no longer matches - otherwise reuses the existing client, since `refine()` is a simple one-shot call with no state worth preserving across profile changes.

## Related
- [D - Log Writer Module](D%20-%20Log%20Writer%20Module.md)
- [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md) (independent `llm_profiles` choice, same centralized `kathrena.llm` mechanism)
