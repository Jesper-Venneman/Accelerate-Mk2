Triggered by saying "edit to log" (or "edit to log, ...") at the start of a recording.

## Behavior (Mk2)
- Routed via a hardcoded synonym-map entry, `"edit to log"` -> the Vocal Journal folder, rather than a project's frontmatter synonyms.
- The leading "edit to log" phrase is stripped from the transcript before writing.
- Appended (not a new file per entry) into one file per calendar day, grouped by the date encoded in the voice log's filename timestamp.
- Skips [E - Refinement and Summarization Module](../Modules/E%20-%20Refinement%20and%20Summarization%20Module.md) entirely - no AI summary, each entry is just the audio embed and its raw transcription.
- File structure: entries appended back-to-back, separated by `---`:
  `Voicelog \ Transcription --- Voicelog \ Transcription --- Voicelog \ Transcription --- ...`
- Entries aren't necessarily final - content may still get reviewed and processed into relevant project logs later (see [I - Project Management Modules](../Modules/I%20-%20Project%20Management%20Modules.md)).

## Related
- [C - Project Router Module](../Modules/C%20-%20Project%20Router%20Module.md)
- [D - Log Writer Module](../Modules/D%20-%20Log%20Writer%20Module.md)
- [Project Log](Project%20Log.md)
- [Unsorted Log](Unsorted%20Log.md)
