"""Ticket service — autonomous support triage."""
import logging
import uuid
from datetime import datetime, timezone
from bson import ObjectId

from xoai.db.mongo import get_db
from xoai.agents.llm_pool import get_agent_config, llm_pool
from xoai.channels.notifier import notify_admin
from xoai.agents.memory import save_message
from xoai.jobs import job_manager
from xoai.prompts.manager import get_prompt

logger = logging.getLogger("xoai.tickets.service")


async def create_ticket(user_id: str, subject: str, message: str) -> str:
    db = get_db()
    doc = {
        "user_id": user_id,
        "subject": subject,
        "status": "open",
        "agent_context": "",
        "admin_notes": "",
        "messages": [{"role": "user", "content": message, "at": datetime.now(timezone.utc).isoformat()}],
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.tickets.insert_one(doc)
    ticket_id = str(result.inserted_id)
    await job_manager.enqueue("ticket_triage", {"ticket_id": ticket_id})
    return ticket_id


async def agent_0_triage(ticket_id: str):
    """Agent 0 analyzes the ticket and routes to Admin Work Chat."""
    db = get_db()
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        return

    # 1. Find an admin to host the Work Chat
    admin = await db.users.find_one({"role": "admin"})
    if not admin:
        logger.error("No admin found to receive support tickets.")
        return

    admin_id = str(admin["_id"])
    work_chat_id = admin.get("active_work_chat_id")

    # 2. Check if Agent 0 is configured
    config = await get_agent_config("agent_0")
    if not config or not config.get("key"):
        error_msg = (
            f"⚠️ [SUPPORT] New ticket from {ticket['user_id']}: {ticket['subject']}\n\n"
            "ERROR: Admin has not initiated Agent 0 properly. Please build and configure A0 correctly in settings."
        )
        await _post_to_work_chat(admin_id, work_chat_id, error_msg)
        return

    # 3. Classify Minor vs Big
    prompt = get_prompt("ticket_triage", subject=ticket["subject"], content=ticket["messages"][0]["content"])
    
    try:
        triage_text = await llm_pool.generate(prompt)
        
        # 4. Route to Work Chat
        is_big = "BIG" in triage_text
        status_tag = "🔴 [BIG CHANGE]" if is_big else "🟡 [MINOR CHANGE]"
        
        message_content = (
            f"--- NEW SUPPORT TICKET ---\n"
            f"{status_tag}\n\n"
            f"{triage_text}\n\n"
            f"Ticket ID: {ticket_id}"
        )
        
        metadata = {
            "type": "triage_approval",
            "ticket_id": ticket_id,
            "classification": "big" if is_big else "minor",
            "at": datetime.now(timezone.utc).isoformat()
        }
        
        await _post_to_work_chat(admin_id, work_chat_id, message_content, metadata)
        
        # 5. Omni-channel Proactive Notification
        await notify_admin(ObjectId(admin_id), f"Ticket Triage: {status_tag} {ticket['subject']}")
        
    except Exception as e:
        logger.error(f"Agent 0 triage failed for ticket {ticket_id}: {e}")


async def _post_to_work_chat(user_id: str, chat_id: str | None, content: str, metadata: dict = None):
    """Posts a message to the persistent Work Chat, creating it if needed."""
    db = get_db()
    
    if not chat_id:
        # Create a new persistent Work Chat
        chat_id = str(uuid.uuid4())
        await db.conversations.insert_one({
            "chat_id": chat_id,
            "user_id": user_id,
            "title": "Admin Work Chat",
            "summary_compressed": None,
            "message_count": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"active_work_chat_id": chat_id}})
    await save_message(
        chat_id,
        "assistant",
        content,
        user_id=user_id,
        channel_metadata=metadata or {},
    )
    logger.info(f"Routed ticket to Work Chat {chat_id}")


async def list_tickets(user_id: str = None, status: str = None):
    db = get_db()
    query = {}
    if user_id:
        query["user_id"] = user_id
    if status:
        query["status"] = status
    tickets = []
    async for t in db.tickets.find(query).sort("created_at", -1):
        t["id"] = str(t.pop("_id"))
        tickets.append(t)
    return tickets
