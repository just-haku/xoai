import logging
from xoai.db.mongo import db
from xoai.chats.service import create_conversation, add_message
from xoai.agents.supervisor import A0_Supervisor

logger = logging.getLogger("xoai.channels.routing")

async def route_incoming_bot_message(user_id: str, platform: str, content: str) -> str:
    """
    Route an incoming message from an external bot to the user's Work Chat.
    Returns the response content to send back.
    """
    user = await db.users.find_one({"_id": user_id})
    if not user:
        return "System Error: User account not found."
        
    work_chat_id = user.get("active_work_chat_id")
    
    if not work_chat_id:
        # Create a new conversation and set it as active work chat
        conv_id = await create_conversation(user_id, platform, "New Work Chat")
        work_chat_id = conv_id
        await db.users.update_one({"_id": user_id}, {"$set": {"active_work_chat_id": work_chat_id}})
        
    # Append the user message
    metadata = {"platform": platform}
    await add_message(work_chat_id, "user", content, channel_metadata=metadata)
    
    # Process with A0 immediately (assuming synchronous wait for simplicity)
    # Pass platform in context so A0 knows where this is happening
    logger.info(f"Routed message from {platform} to Work Chat {work_chat_id}")
    
    # In a full flow, you would yield the response via AI stream, 
    # but for bots, we gather the final string.
    try:
        response_text = ""
        # Mocking or calling the real agent manager
        response_text = f"[Omni-Channel via {platform}] Message received and synced to Work Chat!"
        
        await add_message(work_chat_id, "assistant", response_text, channel_metadata=metadata)
        return response_text
    except Exception as e:
        logger.error(f"Error generating bot response: {e}")
        return "Sorry, the intelligence system encountered an error."
