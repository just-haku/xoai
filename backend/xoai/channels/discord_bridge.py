"""Discord Bridge — Polling/Event based worker."""

import asyncio
import logging
import os
import discord
from discord.ext import commands

from xoai.config import settings
from xoai.agents.supervisor import process_message
from xoai.channels.mapping import get_user_by_channel_id

logger = logging.getLogger("xoai.channels.discord")

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


class DiscordBridge(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def on_ready(self):
        logger.info(f"🚀 Discord Bridge ready: {self.user}")

    async def on_message(self, message):
        if message.author == self.user:
            return

        chat_id = str(message.author.id)
        user = await get_user_by_channel_id("discord", chat_id)
        if not user:
            # Fallback for dev: if it's the admin, map it?
            # For now, just ignore or reply
            return

        conversation_id = f"discord_{chat_id}"
        response_stream = await process_message(user, message.content, conversation_id, channel="discord")
        
        full_response = ""
        if hasattr(response_stream, "__aiter__"):
            async for chunk in response_stream:
                if chunk["type"] == "content":
                    full_response += chunk["content"]
        else:
            full_response = str(response_stream)

        if full_response:
            await message.reply(full_response)


async def start_discord_bridge():
    if not DISCORD_TOKEN:
        logger.warning("DISCORD_BOT_TOKEN missing.")
        return

    bridge = DiscordBridge()
    async with bridge:
        await bridge.start(DISCORD_TOKEN)
