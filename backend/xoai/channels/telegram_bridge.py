"""Telegram Bridge — Polling worker."""

import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from xoai.config import settings
from xoai.agents.supervisor import process_message
from xoai.channels.mapping import get_user_by_channel_id

logger = logging.getLogger("xoai.channels.telegram")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = str(update.message.chat_id)
    user = await get_user_by_channel_id("telegram", chat_id)
    if not user:
        return

    conversation_id = f"telegram_{chat_id}"
    response_stream = await process_message(user, update.message.text, conversation_id, channel="telegram")
    
    full_response = ""
    if hasattr(response_stream, "__aiter__"):
        async for chunk in response_stream:
            if chunk["type"] == "content":
                full_response += chunk["content"]
    else:
        full_response = str(response_stream)

    if full_response:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=full_response)


async def start_telegram_bridge():
    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN missing.")
        return

    logger.info("🚀 Telegram Bridge starting...")
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_telegram_message)
    application.add_handler(msg_handler)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
