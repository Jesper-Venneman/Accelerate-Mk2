The actual surface where you talk to [Kathrena](G%20-%20Kathrena%20Agent%20Core.md) (text or voice), where she talks back, and where [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md)'s proposals get reviewed - previously referenced everywhere as "a chat window" without anything defining what that is.

## Implementation approach
**Chainlit** (Apache-2.0, pure Python, self-hosted, free) - `pip install chainlit`, `@cl.on_message` handles each turn and calls into Kathrena's LangGraph graph in-process, no separate API server or second language ecosystem needed.

- **Approve/Reject/Edit:** rendered as `cl.Action` buttons attached to a proposal message. Clicking one calls back into the paused graph with `Command(resume=...)`, directly matching [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md)'s `interrupt()`/resume design.
- **Visibility:** `@cl.step` surfaces intermediate tool calls (vault search, memory recall, etc.) so you can see what Kathrena is doing, not just the final answer.
- **Voice input:** [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md)'s wake-word listener and [B - Transcription Module](B%20-%20Transcription%20Module.md)'s transcription feed into the same Chainlit session as if typed - one input path for both text and voice, not two separate UIs. No separate push-to-talk mic button in the chat window itself - the wake-word path already covers voice input.
- **Voice output (text-to-speech):** Kathrena's reply is synthesized with **Kokoro-82M** (Apache-2.0, small and fast enough for CPU, better quality than the lighter Piper/pyttsx3 alternatives) and attached to the reply message as an auto-playing `cl.Audio` element. Only turns that came in through the wake-word voice path get spoken back - a typed question gets a typed (silent) answer, since you're already looking at the screen. See [Decisions Log](../Decisions%20Log.md) Round 16.

## Voice persona (Kathrena's voice effects)
Kokoro's raw output is a generic synthesized voice - it doesn't sound like Kathrena's established voice from her earlier, non-public, pre-AI TTS system. A **separate, swappable post-processing stage** sits between Kokoro's output and playback: DSP-only voice effects (pitch/formant shifting, EQ/timbre coloring, other effects for a more robotic voice) reshape the raw synthesis toward that established character.

- **DSP effects, not voice cloning:** an approximate match via signal processing, not a trained voice-conversion/cloning model (e.g. RVC, OpenVoice) - much lighter to build and run, no reference-audio training pipeline needed. True voice cloning is a possible future upgrade if the DSP approximation isn't convincing enough, using reference clips from the Kathrena 1.0 source project (not stored in this repo).
- **Independent of the TTS engine choice:** takes synthesized audio in, returns processed audio out - Kokoro (or a future swap to Piper/anything else) doesn't need to know this stage exists, and the effects chain doesn't need to know which engine produced its input.
- **Independent of Chainlit:** since it's just an audio-in/audio-out step, the same component could feed a future output surface without changes.

## Conversation history across restarts (Decisions Log Round 29)
A restart resumes the last active conversation rather than always starting blank: `on_chat_start` reads a persisted `agent_core.last_thread_id` setting and, if nothing else already claimed that thread this run, resumes it - `kathrena.agent_core.graph.load_thread_messages` reads the thread's messages straight out of [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md)'s existing `SqliteSaver` checkpoint (no new storage, no graph/model construction needed just to read history), and `_replay_history` re-sends the human/AI turns (not tool calls/tool outputs) as regular messages so the UI looks like the conversation never stopped. A second concurrent tab still gets its own fresh thread, same isolation as before this round - only a genuine restart resumes.

Deliberately the lighter of two options considered - see [Chainlit Data Layer](../Investigations/Chainlit%20Data%20Layer.md) for the fuller native alternative (thread-history sidebar, multi-thread switching) that was investigated and documented but not built, since it requires adding an authentication layer to an otherwise zero-auth single-user app.

## Considered and rejected
**LangChain's official Agent Chat UI** (MIT, purpose-built for LangGraph) - a strong alternative, but it's a separate Next.js/TypeScript app that needs a self-hosted LangGraph API server running alongside it as its own deployment surface. That's a second language ecosystem for a personal, single-user project, and its approve/reject flow isn't a built-in polished widget - it would need custom "Artifact" component work on our end. Worth revisiting if we ever want a fancier, more customizable web frontend; Chainlit's Python-native, batteries-included approach fits this project better for now.

**Piper / pyttsx3 (text-to-speech)** - both free/local/no-account, same as Kokoro. Piper is more battle-tested and slightly cheaper to run; pyttsx3 (OS-native SAPI voices) needs no model download at all. Kept on file as fallback options if Kokoro turns out to be too heavy or a poor fit for the voice-persona effects stage. See [Decisions Log](../Decisions%20Log.md) Round 16.

## Note
Chainlit's original core team stepped back in May 2025; it's now community-maintained under a formal agreement. Still active (frequent releases), but worth knowing.

## Related
- [G - Kathrena Agent Core](G%20-%20Kathrena%20Agent%20Core.md)
- [H - Change Proposal and Approval Gate](H%20-%20Change%20Proposal%20and%20Approval%20Gate.md)
- [B - Transcription Module](B%20-%20Transcription%20Module.md)
