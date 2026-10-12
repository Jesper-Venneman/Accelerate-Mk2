Watches a synced drop folder for new voice-log audio files and hands them to [B - Transcription Module](B%20-%20Transcription%20Module.md).

## Responsibilities
- Watch a folder (same drop-folder pattern as Mk1's `VoiceLog_Processor.py`, using `watchdog`).
- Treat every source the same way - phone, desktop, or a future hardware recorder just need to drop a `.wav` into the synced folder. No special-casing per source.
- Hand off newly-seen files to [B - Transcription Module](B%20-%20Transcription%20Module.md).

## Explicitly not our job
- Syncing files between devices - already solved externally.
- Building the ESP32 hardware recorder - future/separate project, but this layer's generic contract already supports it whenever it exists.

## Related
- [B - Transcription Module](B%20-%20Transcription%20Module.md)
- [D - Log Writer Module](D%20-%20Log%20Writer%20Module.md)
