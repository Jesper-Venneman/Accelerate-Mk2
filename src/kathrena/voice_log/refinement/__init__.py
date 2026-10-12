"""Module E: Refinement and Summarization.

Design spec: Architecture/Modules/E - Refinement and Summarization Module.md

Cleans up and summarizes a raw transcript via the hybrid LLM backend (local
oobabooga TextGen by default, cloud optional) before `kathrena.voice_log.log_writer`
(Module D) writes it out.
"""

from kathrena.voice_log.refinement.llm_refiner import LangChainRefiner, Refiner

__all__ = ["LangChainRefiner", "Refiner"]
