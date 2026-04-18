from __future__ import annotations

import logging
import os
from pathlib import Path

import discord
from bson import ObjectId
from telegram import Bot as TelegramBot
from telegram import InputFile as TelegramInputFile

from xoai.auth.service import decrypt_value
from xoai.config import settings
from xoai.db.mongo import get_db

logger = logging.getLogger("xoai.channels.file_delivery")


def get_channel_upload_dir(user_id: str, channel: str) -> Path:
    path = Path(settings.xoai_storage) / "users" / user_id / "workspace" / "_channel_uploads" / channel
    path.mkdir(parents=True, exist_ok=True)
    return path


async def persist_channel_bytes(user_id: str, channel: str, filename: str, payload: bytes) -> str:
    safe_name = Path(filename or "attachment.bin").name
    destination = get_channel_upload_dir(user_id, channel) / safe_name
    destination.write_bytes(payload)
    return str(destination)


async def build_web_file_link(user_id: str, filepath: str) -> str:
    workspace_root = Path(settings.xoai_storage) / "users" / user_id / "workspace"
    relative = Path(filepath).resolve().relative_to(workspace_root.resolve())
    return f"{settings.public_base_url.rstrip('/')}/view-file?path={relative.as_posix()}"


async def deliver_file_to_channel(user_id: str, channel: str, filepath: str) -> str:
    if channel == "zalo":
        return await build_web_file_link(user_id, filepath)
    if channel == "telegram":
        return await _send_telegram_file(user_id, filepath)
    if channel == "discord":
        return await _send_discord_file(user_id, filepath)
    raise ValueError(f"Unsupported channel: {channel}")


async def _send_telegram_file(user_id: str, filepath: str) -> str:
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    chat_id = (user or {}).get("channel_mappings", {}).get("telegram")
    if not chat_id:
        raise ValueError("Telegram channel mapping not found.")
    bot_instance = await db.bot_instances.find_one({"user_id": user_id, "platform": "telegram"})
    if not bot_instance:
        raise ValueError("Telegram bot instance not configured.")
    token = decrypt_value(bot_instance["token_encrypted"])
    bot = TelegramBot(token=token)
    await bot.initialize()
    try:
        with open(filepath, "rb") as handle:
            await bot.send_document(chat_id=chat_id, document=TelegramInputFile(handle, filename=os.path.basename(filepath)))
    finally:
        await bot.shutdown()
    return "Telegram file sent."


async def _send_discord_file(user_id: str, filepath: str) -> str:
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    discord_user_id = (user or {}).get("channel_mappings", {}).get("discord")
    if not discord_user_id:
        raise ValueError("Discord channel mapping not found.")
    bot_instance = await db.bot_instances.find_one({"user_id": user_id, "platform": "discord"})
    if not bot_instance:
        raise ValueError("Discord bot instance not configured.")
    token = decrypt_value(bot_instance["token_encrypted"])
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        target = await client.fetch_user(int(discord_user_id))
        await target.send(file=discord.File(filepath))
        await client.close()

    await client.start(token)
    return "Discord file sent."
