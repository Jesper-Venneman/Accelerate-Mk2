"""Composition root for the voice-log pipeline (Modules A-E).

Design spec: Architecture/Architecture Overview.md (voice-log pipeline, A-E)
Run with: `python -m kathrena.voice_log.pipeline`

This is the only file that imports all five modules together. Each module stays
independently testable and swappable on its own; this file just wires them into
each other in the order a transcript flows: watch -> transcribe -> route -> refine -> write.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from kathrena.config import PipelineConfig
from kathrena.voice_log.ingestion import VoiceLogWatcher, parse_recorded_at
from kathrena.voice_log.log_writer import LogEntry, write_log
from kathrena.voice_log.project_router import LogType, build_synonym_map, route
from kathrena.voice_log.refinement import Refiner
from kathrena.voice_log.transcription import Transcriber

logger = logging.getLogger(__name__)


class VoiceLogPipeline:
    """Ties Modules A-E together: watch -> transcribe -> route -> refine -> write."""

    def __init__(self, config: PipelineConfig, transcriber: Transcriber, refiner: Refiner) -> None:
        self._config = config
        self._transcriber = transcriber
        self._refiner = refiner
        self._synonym_map = build_synonym_map(config)
        self._watcher = VoiceLogWatcher(config, on_new_log=self._process)

    def run_forever(self) -> None:
        """Process any backlog, then watch for new voice logs until `stop()` is called."""
        self._watcher.process_existing()
        self._watcher.start()

    def stop(self) -> None:
        self._watcher.stop()

    def _process(self, audio_path: Path) -> None:
        logger.info("New voice log: %s", audio_path.name)
        transcription = self._transcriber.transcribe(audio_path)
        recorded_at = parse_recorded_at(audio_path)
        route_result = route(transcription.text, self._synonym_map, self._config)

        summary = None
        if route_result.log_type is not LogType.VOCAL_JOURNAL:
            summary = self._refiner.refine(transcription.text)

        entry = LogEntry(
            audio_path=audio_path,
            transcript=transcription.text,
            recorded_at=recorded_at,
            route=route_result,
            summary=summary,
        )
        written_path = write_log(self._config, entry)
        logger.info("Wrote %s log to %s", route_result.log_type.value, written_path)

        self._watcher.mark_processed(audio_path)


def main() -> None:
    from kathrena.settings import SettingsNotConfiguredError, ensure_configured
    from kathrena.voice_log.refinement import LangChainRefiner
    from kathrena.voice_log.transcription import WhisperTranscriber

    logging.basicConfig(level=logging.INFO)
    try:
        ensure_configured()
    except SettingsNotConfiguredError as exc:
        raise SystemExit(str(exc)) from exc
    config = PipelineConfig()
    pipeline = VoiceLogPipeline(
        config=config,
        transcriber=WhisperTranscriber(config),
        refiner=LangChainRefiner(config),
    )
    pipeline.run_forever()
    try:
        while True:
            time.sleep(1)  # watchdog's Observer runs on its own thread; keep the process alive.
    except KeyboardInterrupt:
        pipeline.stop()


if __name__ == "__main__":
    main()
