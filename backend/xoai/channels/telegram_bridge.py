"""Telegram Bridge — polling worker with attachment persistence."""

from __future__ import annotations

import logging
from pathlib import Path

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters

from xoai.agents.supervisor import process_message
from xoai.channels.file_delivery import persist_channel_bytes
from xoai.channels.mapping import get_user_by_channel_id

logger = logging.getLogger("xoai.channels.telegram")

_tenant_apps: dict[str, Application] = {}


async def _download_telegram_attachment(update: Update, user: dict) -> list[str]:
    message = update.message
    if not message:
        return []
    stored_paths: list[str] = []
    candidates = []
    if message.document:
        candidates.append((message.document.file_id, message.document.file_name or "document.bin"))
    if message.photo:
        photo = message.photo[-1]
        candidates.append((photo.file_id, f"photo_{photo.file_unique_id}.jpg"))

    for file_id, filename in candidates:
        tg_file = await message.get_bot().get_file(file_id)
        payload = await tg_file.download_as_bytearray()
        stored_paths.append(await persist_channel_bytes(str(user["_id"]), "telegram", filename, bytes(payload)))
    return stored_paths


async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    chat_id = str(message.chat_id)
    user = await get_user_by_channel_id("telegram", chat_id)
    if not user:
        return

    stored_paths = await _download_telegram_attachment(update, user)
    text = (message.text or message.caption or "").strip()
    if stored_paths:
        attachment_lines = "\n".join(f"Attachment saved: {Path(path).name}" for path in stored_paths)
        text = f"{text}\n\n{attachment_lines}".strip()
    if not text:
        text = "User sent an attachment without text."

    conversation_id = f"telegram_{chat_id}"
    response_stream = await process_message(user, text, conversation_id, channel="telegram")

    full_response = ""
    if hasattr(response_stream, "__aiter__"):
        async for chunk in response_stream:
            if chunk["type"] == "content":
                full_response += chunk["content"]
    else:
        full_response = str(response_stream)

    if full_response:
        await context.bot.send_message(chat_id=message.chat_id, text=full_response)


async def start_tenant_telegram(user_id: str, token: str):
    if user_id in _tenant_apps:
        logger.info("Telegram tenant already running", extra={"user_id": user_id})
        return

    logger.info("Telegram Bridge starting", extra={"user_id": user_id})
    application = ApplicationBuilder().token(token).build()
    application.add_handler(
        MessageHandler(filters.ALL & (~filters.COMMAND), handle_telegram_message)
    )
    _tenant_apps[user_id] = application

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    try:
        await application.updater.wait_until_closed()
    finally:
        await application.stop()
        await application.shutdown()
        _tenant_apps.pop(user_id, None)
