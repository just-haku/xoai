"""Discord Bridge — event worker with attachment persistence."""

from __future__ import annotations

import logging
from pathlib import Path

import discord
from discord.ext import commands

from xoai.agents.supervisor import process_message
from xoai.channels.file_delivery import persist_channel_bytes
from xoai.channels.mapping import get_user_by_channel_id

logger = logging.getLogger("xoai.channels.discord")

_tenant_bots: dict[str, commands.Bot] = {}


class DiscordBridge(commands.Bot):
    def __init__(self, user_id: str):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        super().__init__(command_prefix="!", intents=intents)
        self.user_id = user_id

    async def on_ready(self):
        logger.info("Discord Bridge ready", extra={"user_id": self.user_id, "bot_user": str(self.user)})

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        chat_id = str(message.author.id)
        user = await get_user_by_channel_id("discord", chat_id)
        if not user:
            return

        attachment_paths = []
        for attachment in message.attachments:
            payload = await attachment.read()
            attachment_paths.append(
                await persist_channel_bytes(str(user["_id"]), "discord", attachment.filename or "attachment.bin", payload)
            )

        text = (message.content or "").strip()
        if attachment_paths:
            attachment_lines = "\n".join(f"Attachment saved: {Path(path).name}" for path in attachment_paths)
            text = f"{text}\n\n{attachment_lines}".strip()
        if not text:
            text = "User sent an attachment without text."

        conversation_id = f"discord_{chat_id}"
        response_stream = await process_message(user, text, conversation_id, channel="discord")

        full_response = ""
        if hasattr(response_stream, "__aiter__"):
            async for chunk in response_stream:
                if chunk["type"] == "content":
                    full_response += chunk["content"]
        else:
            full_response = str(response_stream)

        if full_response:
            await message.reply(full_response)


async def start_tenant_discord(user_id: str, token: str):
    if user_id in _tenant_bots:
        logger.info("Discord tenant already running", extra={"user_id": user_id})
        return

    bridge = DiscordBridge(user_id)
    _tenant_bots[user_id] = bridge
    try:
        async with bridge:
            await bridge.start(token)
    finally:
        _tenant_bots.pop(user_id, None)

