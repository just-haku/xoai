"""Ticket service — autonomous support triage."""

import logging
from datetime import datetime, timezone

from xoai.db.mongo import get_db

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
    # TODO: Phase 8 — Agent 0 auto-triage + admin notification
    return str(result.inserted_id)


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
