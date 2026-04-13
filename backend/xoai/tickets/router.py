"""Ticket management router for admins."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from xoai.auth.dependencies import require_admin
from xoai.db.mongo import get_db

router = APIRouter()


@router.get("/")
async def list_tickets(admin: dict = Depends(require_admin)):
    """List all tickets across the platform."""
    db = get_db()
    cursor = db.tickets.find().sort("created_at", -1)
    tickets = await cursor.to_list(100)
    # Convert ObjectIds to strings
    for t in tickets:
        t["id"] = str(t.pop("_id"))
    return tickets


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, admin: dict = Depends(require_admin)):
    """Get details for a specific ticket."""
    from bson import ObjectId
    db = get_db()
    ticket = await db.tickets.find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket["id"] = str(ticket.pop("_id"))
    return ticket


@router.patch("/{ticket_id}")
async def update_ticket(ticket_id: str, update: dict, admin: dict = Depends(require_admin)):
    """Update ticket status or notes."""
    from bson import ObjectId
    db = get_db()
    await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": update}
    )
    return {"status": "ok"}
