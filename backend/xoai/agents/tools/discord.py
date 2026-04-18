"""Discord tool helpers."""

from __future__ import annotations

from pathlib import Path

from xoai.channels.file_delivery import deliver_file_to_channel


async def send_discord_file(filepath: str, user_id: str) -> str:
    if not Path(filepath).is_file():
        return "Error: file not found."
    return await deliver_file_to_channel(user_id, "discord", filepath)

