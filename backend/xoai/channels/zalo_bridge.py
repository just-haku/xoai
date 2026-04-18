"""Zalo polling bridge with defensive empty-payload handling."""

from __future__ import annotations

import asyncio
import logging

from zalo_bot import Bot

from xoai.agents.supervisor import process_message
from xoai.channels.mapping import get_user_by_channel_id

logger = logging.getLogger("xoai.channels.zalo")

ZALO_ATTACHMENT_FALLBACK = (
    "I cannot read this attachment via Zalo. Please open your MangOS Web Interface to upload and view this file."
)


async def handle_zalo_update(update, bot):
    if not update or not getattr(update, "message", None):
        return

    chat_id = str(update.message.chat.id)
    text = (getattr(update.message, "text", None) or "").strip()
    attachments = getattr(update.message, "attachments", None) or []
    has_attachment = bool(attachments)

    user = await get_user_by_channel_id("zalo", chat_id)
    if not user:
        await bot.send_message(chat_id, f"Unauthorized Zalo ID: {chat_id}. Please link this ID via Web Portal.")
        return

    if not text and has_attachment:
        await bot.send_message(chat_id, ZALO_ATTACHMENT_FALLBACK)
        return
    if not text and not has_attachment:
        await bot.send_message(chat_id, "No readable text was included in your Zalo message.")
        return

    conversation_id = f"zalo_{chat_id}"
    response_stream = await process_message(user, text, conversation_id, channel="zalo")

    full_response = ""
    if hasattr(response_stream, "__aiter__"):
        async for chunk in response_stream:
            if chunk["type"] == "content":
                full_response += chunk["content"]
    else:
        full_response = str(response_stream)

    if full_response:
        await bot.send_message(chat_id, full_response)


async def start_tenant_zalo(user_id: str, token: str):
    logger.info("Zalo Bridge starting", extra={"user_id": user_id})
    bot = Bot(token)
    while True:
        try:
            update = await bot.get_update(timeout=45)
            if update and getattr(update, "message", None):
                asyncio.create_task(handle_zalo_update(update, bot))
        except Exception as exc:
            logger.error("Zalo polling error: %s", exc)
            await asyncio.sleep(5)

