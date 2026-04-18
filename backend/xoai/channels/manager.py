import asyncio
import logging

from xoai.auth.service import decrypt_value

logger = logging.getLogger("xoai.channels.manager")

# Dictionary to track running bot tasks for each user/platform
# Format: {(user_id, platform): asyncio.Task}
_active_bots = {}

async def restart_bot_instance(user_id: str, platform: str, token: str):
    """Dynamically start or restart a bot runner for a specific user and platform."""
    logger.info(f"Restarting dynamic bot for {user_id} on {platform}")
    
    # Stop existing if running
    await stop_bot_instance(user_id, platform)
    
    # Start new
    if platform == "telegram":
        from xoai.channels.telegram_bridge import start_tenant_telegram
        task = asyncio.create_task(start_tenant_telegram(user_id, token))
    elif platform == "discord":
        from xoai.channels.discord_bridge import start_tenant_discord
        task = asyncio.create_task(start_tenant_discord(user_id, token))
    elif platform == "zalo":
        from xoai.channels.zalo_bridge import start_tenant_zalo
        task = asyncio.create_task(start_tenant_zalo(user_id, token))
    else:
        return
        
    _active_bots[(user_id, platform)] = task

async def stop_bot_instance(user_id: str, platform: str):
    """Stop a running bot instance."""
    logger.info(f"Stopping dynamic bot for {user_id} on {platform}")
    if (user_id, platform) in _active_bots:
        task = _active_bots.pop((user_id, platform))
        task.cancel()
        
async def load_all_tenant_bots():
    """Called on startup to resume all user bots from DB."""
    from xoai.db.mongo import db
    
    cursor = db.bot_instances.find({"status": "active"})
    async for instance in cursor:
        try:
            token = decrypt_value(instance["token_encrypted"])
            await restart_bot_instance(instance["user_id"], instance["platform"], token)
        except Exception as e:
            logger.error(f"Failed to load bot {instance['_id']}: {e}")
