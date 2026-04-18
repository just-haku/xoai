"""Telegram bot channel helpers."""

import logging

from xoai.channels.file_delivery import deliver_file_to_channel

logger = logging.getLogger("xoai.channels.telegram")


async def start_telegram_polling():
    """Start the Telegram bot polling engine."""
    logger.info("Telegram polling: not yet configured.")


async def send_file_to_telegram_user(user_id: str, filepath: str) -> str:
    return await deliver_file_to_channel(user_id, "telegram", filepath)
