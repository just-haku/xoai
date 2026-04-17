"""Notifier Service — Proactive omni-channel alerts."""
import logging
from xoai.db.mongo import get_db

logger = logging.getLogger("xoai.notifier")

async def notify_admin(user_id: str, message: str):
    """
    Push a notification to an admin's linked external channels.
    This uses the existing bot instances if active.
    """
    db = get_db()
    user = await db.users.find_one({"_id": user_id})
    if not user:
        return

    # 1. Internal Log
    logger.info(f"Proactive notification for {user_id}: {message[:50]}...")

    # 2. Extract mappings
    mappings = user.get("channel_mappings", {})
    
    # 3. Handle Telegram
    if "telegram" in mappings:
        try:
            from telegram import Bot
            from xoai.auth.service import decrypt_key
            
            instance = await db.bot_instances.find_one({"user_id": str(user_id), "platform": "telegram"})
            if instance:
                token = decrypt_key(instance["token_encrypted"])
                bot = Bot(token=token)
                await bot.initialize()
                await bot.send_message(chat_id=mappings["telegram"], text=message)
                logger.info("Sent Telegram notification.")
        except Exception as e:
            logger.error(f"Failed to push Telegram notification: {e}")

    # 4. Handle Discord
    # Discord requires an active client loop or a webhook. 
    # For now, we log the intent as the tenant bots are running in separate tasks.
    if "discord" in mappings:
        logger.info(f"Discord notification queued for author_id {mappings['discord']}")

    # 5. Handle Zalo
    if "zalo" in mappings:
        logger.info(f"Zalo notification intent: {mappings['zalo']}")
