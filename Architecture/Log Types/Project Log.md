The default case: a voice log that [C - Project Router Module](../Modules/C%20-%20Project%20Router%20Module.md) matched to a project via its alias.

## Behavior (Mk2)
- Sorted to whichever project's alias is heard first in the transcript.
- Each recording produces a new file (never appended).
- File structure, split into three parts separated by `---`:
  `Voicelog --- Transcription --- AI Summary`
- Goes through [E - Refinement and Summarization Module](../Modules/E%20-%20Refinement%20and%20Summarization%20Module.md) to produce the AI Summary section.
- Written into the matched project's `Ω - logs` folder by [D - Log Writer Module](../Modules/D%20-%20Log%20Writer%20Module.md).

## Related
- [C - Project Router Module](../Modules/C%20-%20Project%20Router%20Module.md)
- [D - Log Writer Module](../Modules/D%20-%20Log%20Writer%20Module.md)
- [Unsorted Log](Unsorted%20Log.md)
- [Vocal Journal](Vocal%20Journal.md)
