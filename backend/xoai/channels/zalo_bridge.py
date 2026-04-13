"""Zalo Polling Bridge — Migrated from legacy agent.py."""

import asyncio
import logging
import os
from zalo_bot import Bot
from zalo_bot.ext import ApplicationBuilder, MessageHandler, filters

from xoai.config import settings
from xoai.agents.supervisor import process_message
from xoai.channels.mapping import get_user_by_channel_id

logger = logging.getLogger("xoai.channels.zalo")

# We'll use a global bot instance configured via DB/Env
ZALO_TOKEN = os.getenv("ZALO_BOT_TOKEN")


async def start_zalo_bridge():
    """Start the Zalo polling worker."""
    if not ZALO_TOKEN:
        logger.warning("ZALO_BOT_TOKEN missing. Zalo bridge not started.")
        return

    logger.info("🚀 Zalo Bridge starting...")
    bot = Bot(ZALO_TOKEN)
    
    # Simple polling loop similar to agent.py
    while True:
        try:
            update = await bot.get_update(timeout=45)
            if update and hasattr(update, "message") and update.message:
                asyncio.create_task(handle_zalo_update(update, bot))
        except Exception as e:
            logger.error(f"Zalo polling error: {e}")
            await asyncio.sleep(5)


async def handle_zalo_update(update, bot):
    """Handle incoming Zalo message."""
    chat_id = str(update.message.chat.id)
    text = update.message.text or ""
    
    # 1. Map to internal user
    user = await get_user_by_channel_id("zalo", chat_id)
    if not user:
        # TODO: Handle unauthorized or OTP flow from agent.py
        await bot.send_message(chat_id, f"Unauthorized Zalo ID: {chat_id}. Please link this ID via Web Portal.")
        return

    # 2. Get/Create conversation (simplified for Phase 5)
    conversation_id = f"zalo_{chat_id}"
    
    # 3. Process via supervisor
    response_stream = await process_message(user, text, conversation_id, channel="zalo")
    
    # 4. Handle response (Collect and send)
    full_response = ""
    if hasattr(response_stream, "__aiter__"):
        async for chunk in response_stream:
            if chunk["type"] == "content":
                full_response += chunk["content"]
            # Handle tool status if needed
    else:
        full_response = str(response_stream)
        
    if full_response:
        await bot.send_message(chat_id, full_response)
