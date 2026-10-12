Converts raw audio into text for [C - Project Router Module](C%20-%20Project%20Router%20Module.md).

## Responsibilities
- Speech-to-text using **openai-whisper** (the original, MIT-licensed Whisper package) - see [Decisions Log](../Decisions%20Log.md) Round 15 for why this replaced faster-whisper.
- Kept swappable behind a small interface so the model/engine can change without touching the rest of the pipeline.

## Related
- [A - Ingestion and Sync Layer](A%20-%20Ingestion%20and%20Sync%20Layer.md)
- [C - Project Router Module](C%20-%20Project%20Router%20Module.md)
