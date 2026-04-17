from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from xoai.auth.dependencies import require_admin
from xoai.auth.router import get_current_user
from xoai.db.mongo import get_db
from xoai.tickets import service

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


@router.post("/")
async def submit_ticket(data: dict, user: dict = Depends(get_current_user)):
    """User submits a new support ticket."""
    subject = data.get("subject", "General Inquiry")
    message = data.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    ticket_id = await service.create_ticket(user["id"], subject, message)
    return {"status": "ok", "ticket_id": ticket_id}


@router.post("/{ticket_id}/approve")
async def approve_ticket(ticket_id: str, admin: dict = Depends(require_admin)):
    """Admin approves Agent 0's triage result."""
    from bson import ObjectId
    db = get_db()
    
    result = await db.tickets.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    return {"status": "ok", "message": "Ticket approved for multi-agent resolution."}


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
