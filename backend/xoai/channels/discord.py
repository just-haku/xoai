"""Discord bot channel helpers."""

import logging

from xoai.channels.file_delivery import deliver_file_to_channel

logger = logging.getLogger("xoai.channels.discord")


async def start_discord_bot():
    """Start the Discord bot engine."""
    logger.info("Discord bot: not yet configured.")


async def send_file_to_discord_user(user_id: str, filepath: str) -> str:
    return await deliver_file_to_channel(user_id, "discord", filepath)
