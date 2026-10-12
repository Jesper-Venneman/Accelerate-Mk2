Logs that are neither a [Vocal Journal](Vocal%20Journal.md) entry nor matched to a known project by [C - Project Router Module](../Modules/C%20-%20Project%20Router%20Module.md) - possibly a new project, or an existing one whose alias wasn't mentioned or wasn't recognized while transcribing.

## Behavior (Mk2)
- Handled exactly like a [Project Log](Project%20Log.md): one new file per recording, same `Voicelog --- Transcription --- AI Summary` structure, goes through [E - Refinement and Summarization Module](../Modules/E%20-%20Refinement%20and%20Summarization%20Module.md).
- Only difference: written into a dedicated "Unsorted Logs" folder instead of a project's `Ω - logs` folder.

## Related
- [C - Project Router Module](../Modules/C%20-%20Project%20Router%20Module.md)
- [D - Log Writer Module](../Modules/D%20-%20Log%20Writer%20Module.md)
- [Project Log](Project%20Log.md)
