Gives [Kathrena](G%20-%20Kathrena%20Agent%20Core.md) a visual sense of what's on screen - a genuinely new
sensory modality, not just another text tool - so she can answer questions about what you're
currently looking at, and (stretch goal) eventually notice things unprompted.

**Status: design only, not built yet** - deferred per Round 22 until the open questions below
(especially TextGen's actual vision support) are verified hands-on.

## Responsibilities
- An on-demand tool (e.g. `view_screen`) [Kathrena](G%20-%20Kathrena%20Agent%20Core.md) can call mid-conversation to see what's currently on screen and answer questions about it.
- **Stretch goal, in scope for the eventual build (not a separate later phase):** a background loop that periodically captures the screen and can prompt Kathrena to react proactively to what changed - see Proactive stretch goal below. Structurally the same shape as [J - Memory Module](J%20-%20Memory%20Module.md): an on-demand tool plus an independent background process, not just a bound tool like `search_web`.
- Deliberately excluded: continuous/real-time vision, or reacting to every frame - both explicitly ruled out (Round 22) as too resource-heavy for a background capability that must stay cheap by default.

## Capture scope
Only the active/foreground window, not the whole desktop across all monitors (Round 22) - least
exposure: whatever you're currently focused on, not unrelated apps/windows that happen to be open.

**Candidate packages** (none added yet - nothing is built):
- **Pixel capture: `mss`** (MIT, confirmed) - fast, cross-platform, no GUI toolkit dependency, ctypes-based (no compiled extension). Captures a monitor or an arbitrary pixel region; it doesn't know about "windows" itself, so it needs to be told the active window's bounding box (below).
- **Finding the active window's bounding box is platform-specific** - the same kind of per-OS split already accepted for push-to-talk (Round 18):
  - **Windows:** `pywin32` (PSF-2.0, confirmed) - `win32gui.GetForegroundWindow()` + `win32gui.GetWindowRect()`. A pure-`ctypes` call to `user32.dll` (`GetForegroundWindow`/`GetWindowRect`) would avoid the dependency entirely, at the cost of a bit more boilerplate - worth comparing both once building.
  - **Linux/X11:** `python-xlib` (LGPL-2.1+, confirmed) directly, or `ewmh` (wraps `python-xlib` for the `_NET_ACTIVE_WINDOW` convention most EWMH-compliant window managers support - GNOME, KDE, XFCE, etc.) for a simpler API.
  - **Wayland:** same limitation already documented for push-to-talk (Round 18) - a compositor security restriction, not something a library can fully work around. Accept as a known gap, same as push-to-talk's Wayland note.
  - **macOS:** not a primary target for this project, but `pyobjc`'s `Quartz` APIs are the equivalent if ever needed - not investigated further here.

## Vision backend (open question, unresolved)
The core blocker: turning a screenshot into something Kathrena can reason about needs a
vision-capable (multimodal) model, and it's not yet confirmed whether this project's existing
TextGen (oobabooga) server/loaded model actually exposes that over its OpenAI-compatible API in a
way `langchain-openai`'s multimodal message format (`image_url` content blocks) can drive.

A repo-level check of `oobabooga/text-generation-webui` for `image_url`/`multimodal` support
turned up nothing, but that search was narrow and inconclusive - it may just be under a different
name (e.g. a `--mmproj` vision-projector flag on the llama.cpp loader, or a specific extension) and
needs verifying hands-on against the actual running server/model, not by more code searching.
Deferred until that can be tested directly (Round 22).

**Target message format, regardless of backend:** LangChain's standard multimodal content blocks -
`HumanMessage(content=[{"type": "text", "text": ...}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}])`. Any `BaseChatModel` that supports vision accepts this same shape, so
whichever backend is eventually chosen, the code that builds the message stays the same - only
`init_chat_model(...)`'s arguments change. This keeps the vision backend swappable behind the same
kind of Protocol as `VectorStore`/`MemoryProvider`/`WebSearch`.

**If TextGen turns out not to support it cleanly**, candidate fallbacks (a **separate, dedicated
local vision model/server** just for this tool, decoupled from Kathrena's main conversational
model) - none evaluated hands-on yet, in rough order of how well they're documented for exactly
this OpenAI-compatible-API-plus-vision use case:
- **Ollama** (MIT) - the most straightforward option: `langchain-ollama`'s `ChatOllama` has native
  multimodal message support, and Ollama's own OpenAI-compatible endpoint accepts base64 images
  directly. Well-documented vision model support (`llava`, `moondream`, `qwen2-vl`, `minicpm-v`,
  etc.), simple `ollama pull <model>` workflow.
- **llama.cpp's own `llama-server`** - likely the same underlying engine TextGen's loader may use
  for GGUF vision models (`--mmproj` flag); exposes an OpenAI-compatible endpoint with image
  support directly, if TextGen's own wrapping of it turns out to be the problem rather than the
  engine itself.
- **LM Studio** - has a GUI-driven local OpenAI-compatible server with vision model support too,
  but it's a GUI app, not as scriptable/automatable as Ollama or `llama-server` - lower priority
  given this project favors things it can configure/control programmatically.

**Candidate small local vision models** (not evaluated hands-on yet - the resource-consciousness
called out for the proactive stretch goal favors starting with something small and cheap over
the largest/most capable option):
- **moondream2** (Apache-2.0) - purpose-built to be tiny (~2B) and fast for exactly this kind of
  lightweight image captioning/QA task - a strong first candidate for the proactive polling loop
  specifically, where cost-per-check matters most.
- **Qwen2-VL / MiniCPM-V** - stronger quality at a still-modest size (2B-8B range), worth trying if
  moondream2's answers prove too shallow for the on-demand tool's use case.
- **LLaVA** - larger, well-known, more capable, but heavier - a fallback if the smaller models
  underperform, not a first choice given the resource concerns already raised.
- Model license terms vary and can be more idiosyncratic than package licenses (e.g. some
  Llama-derived checkpoints carry usage restrictions) - verify the specific checkpoint's license
  at build time rather than assuming.

## Cloud vision candidates
If local vision proves too weak or slow, and the explicit opt-in (below) is exercised: **GPT-4o /
GPT-4o-mini** (via the already-used `langchain-openai`) or **Claude** (via the `langchain-anthropic`
package already declared in `pyproject.toml`'s `cloud` extra, Decisions Log Round 10) are both
vision-capable and need **zero new dependencies** - only a config/model-name change, since
`init_chat_model(...)` plus the same multimodal message format already works with either. The
opt-in requirement (below) is a policy gate on top of this, not a technical one.

## Cloud policy
Local-only by default; a cloud vision provider is allowed only as an **explicit opt-in** (Round
22) - not automatic, and not the default, even though it would sidestep the TextGen question
above. Consistent with this project's free/local-by-default preference (Decisions Log Round 1),
but screenshots are enough more sensitive than a text query that "opt-in, not silent" matters here
specifically, unlike e.g. the existing `cloud` optional-dependency group for text models.

## Persistence
Never saved to disk by default - captured, sent to the model, discarded. An optional debug flag
(off by default) to save the last screenshot to disk for troubleshooting is in scope, but off
unless explicitly turned on (Round 22).

## Image handling
A few implementation details worth deciding up front rather than rediscovering mid-build:
- **Format:** PNG (lossless, simple) for the capture itself; `mss.tools.to_png` or a `Pillow`
  conversion both work. `Pillow` is already a transitive dependency of this project's existing
  ML stack, so likely no new dependency needed here either way.
- **Resizing before sending:** most vision models internally downscale to a fixed resolution
  anyway (often ~512-768px on the long edge) - resizing client-side first keeps the base64
  payload (and therefore latency/bandwidth) down without losing anything the model would've used
  regardless. Worth doing regardless of which backend is chosen.
- **Encoding:** base64 data-URI (`data:image/png;base64,...`), matching the standard LangChain
  `image_url` content block shape noted above.

## Proactive stretch goal
A background loop that periodically captures the screen and can prompt Kathrena to react without
being asked - the same category of "genuinely agentic, not just tool-using" capability as
[I - Project Management Modules](I%20-%20Project%20Management%20Modules.md)'s I3/I4 sub-agents and [J - Memory Module](J%20-%20Memory%20Module.md)'s background
reflection. Must poll far from constantly (minutes, not seconds) and avoid constant processing -
resource cost was explicitly called out as a concern, not just a nice-to-have constraint.

**Design ideas to validate when building, not yet committed to:**
- **Cheap pre-filter before ever calling the vision model:** compare each new capture against the
  previous one with a cheap perceptual/pixel hash (e.g. the `imagehash` package, BSD-2) and skip
  the vision-model call entirely if nothing meaningfully changed - the vision model (the expensive
  part) only runs when the screen actually looks different, not on every poll tick.
- **A second, separate cooldown for actually messaging you** - even if the vision model says
  something changed/is worth mentioning, a minimum gap between proactive messages (independent of
  the polling interval) avoids being naggy if the screen happens to change often.
- **Delivery into [K - Chat Interface](K%20-%20Chat%20Interface.md):** likely the same `asyncio.Queue` pattern push-to-talk
  already uses (`listener.utterances` - background thread/task produces, the Chainlit app consumes
  and turns it into a `cl.Message`) - a proactive "observation worth mentioning" queue would slot
  into the same per-session lifecycle (start in `on_chat_start`, stop in `on_chat_end`).

Exact polling interval, what triggers an actual reaction (vs. silently re-capturing and discarding),
and the concrete delivery mechanism are all still open - to be designed/validated once the
on-demand tool and vision backend are proven out, not before.

## Testing approach
Following this codebase's established pattern (`FakeVectorStore`, `FakeMemoryProvider`,
`FakeWebSearch`): both the screen-capture step and the vision-model call should sit behind their
own small Protocols (e.g. a `ScreenCapture` returning raw image bytes, and a vision-capable
`WebSearch`-style Protocol wrapping whatever backend is chosen), so tests can inject fake captures
and fake model responses - no real display, GPU, or vision model needed to test the tool-calling
plumbing itself. Real end-to-end validation (actual screenshot -> actual vision model -> sensible
answer) stays a manual/hands-on smoke test, same as how Module J's real `SqliteStore`/embeddings
integration was validated outside the automated test suite.

## Open questions / next steps
1. **Verify hands-on** whether the running TextGen server/model actually accepts image input over
   its OpenAI-compatible API, and in what format - the single blocker everything else depends on.
2. If not: try a candidate local vision backend (Ollama first, per the Vision backend section
   above) with a small model (moondream2 first) and validate quality/latency are good enough.
3. Pick and validate the active-window-capture approach per platform (`mss` + `pywin32`/ctypes on
   Windows, `mss` + `python-xlib`/`ewmh` on Linux/X11).
4. Only then: design the actual `view_screen` tool signature, the proactive polling loop's cheap
   pre-filter and cooldown logic, and how a proactive observation reaches [K - Chat Interface](K%20-%20Chat%20Interface.md)
   mid-session.

## Related
- [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md) - the tool-calling loop this plugs into
- [J - Memory Module](J%20-%20Memory%20Module.md) - closest structural precedent (on-demand tool + background process)
- [I - Project Management Modules](I%20-%20Project%20Management%20Modules.md) - I3/I4, the other "proactive sub-agent" precedents
