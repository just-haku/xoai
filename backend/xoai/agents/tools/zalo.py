"""Zalo-specific tools — stickers + file sending."""

import logging
logger = logging.getLogger("xoai.agents.tools.zalo")


async def send_zalo_sticker(sticker_id: str, user_zalo_id: str) -> str:
    # TODO: Phase 5 — Implement with Zalo OA API
    return "Error: Zalo tools not yet configured."


async def send_zalo_file(filepath: str, user_zalo_id: str) -> str:
    # TODO: Phase 5
    return "Error: Zalo tools not yet configured."
