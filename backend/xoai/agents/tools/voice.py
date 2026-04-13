"""Voice tools — STT/TTS. Provider configured via admin dashboard."""

import logging
logger = logging.getLogger("xoai.agents.tools.voice")


async def speech_to_text(audio_path: str) -> str:
    # TODO: Phase 3 — Google Cloud STT or configurable provider
    return "Error: STT not yet configured."


async def text_to_speech(text: str, output_path: str) -> str:
    # TODO: Phase 3 — Google Cloud TTS or configurable provider
    return "Error: TTS not yet configured."
