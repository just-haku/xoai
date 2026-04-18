"""Zalo-specific tools — stickers + file sending."""

import logging
from pathlib import Path

from xoai.channels.file_delivery import deliver_file_to_channel

logger = logging.getLogger("xoai.agents.tools.zalo")


async def send_zalo_sticker(sticker_id: str, user_zalo_id: str) -> str:
    # TODO: Phase 5 — Implement with Zalo OA API
    return "Error: Zalo tools not yet configured."


async def send_zalo_file(filepath: str, user_zalo_id: str) -> str:
    if not Path(filepath).is_file():
        return "Error: file not found."
    return await deliver_file_to_channel(user_zalo_id, "zalo", filepath)
