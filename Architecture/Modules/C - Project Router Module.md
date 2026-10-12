Figures out which project a transcript belongs to.

## Responsibilities
- Reuses Mk1's synonym-map logic: read each project's `{Project}.md` frontmatter `synonyms:` list, map lowercase synonym to project folder.
- Find the earliest-mentioned synonym in the transcript, route to that project as a [Project Log](../Log%20Types/Project%20Log.md); fall back to [Unsorted Log](../Log%20Types/Unsorted%20Log.md) when nothing matches (new/unrecognized project).
- Keeps the special "edit to log" -> [Vocal Journal](../Log%20Types/Vocal%20Journal.md) case.

## Related
- [B - Transcription Module](B%20-%20Transcription%20Module.md)
- [D - Log Writer Module](D%20-%20Log%20Writer%20Module.md)
- [Project Log](../Log%20Types/Project%20Log.md)
