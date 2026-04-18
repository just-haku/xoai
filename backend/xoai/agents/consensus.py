"""Consensus state machine — two-step idempotent resource hashing for
high-risk tool execution.

Phase 2 of Operation Titan: implements a full resource-hash / verify / commit
cycle that prevents race conditions when multiple agents or users modify the
same resource during the verification window.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from xoai.config import settings
from xoai.db.mongo import get_db

logger = logging.getLogger("xoai.agents.consensus")


@dataclass
class ResourceSnapshot:
    """Captures the state of a target resource at proposal time."""

    resource_type: str  # "file", "db_document", "state"
    resource_key: str  # file path, document id, etc.
    content_hash: str  # SHA-256 of the content at proposal time
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ConsensusProposal:
    """An idempotent proposal for a high-risk action."""

    proposal_id: str
    acting_agent: str
    tool_name: str
    args: dict
    user_id: str
    conversation_id: str
    resource_snapshot: ResourceSnapshot | None = None
    status: str = "pending"  # pending | approved | rejected | committed | stale
    verifier_feedback: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def compute_file_hash(path: str) -> str:
    """Return SHA-256 hex of file contents, or empty string if not accessible."""
    try:
        abs_path = Path(path).resolve()
        if not abs_path.is_file():
            return ""
        hasher = hashlib.sha256()
        with open(abs_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, PermissionError):
        return ""


def compute_content_hash(content: str | bytes) -> str:
    """Return SHA-256 hex of arbitrary content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


async def capture_resource_snapshot(
    tool_name: str, args: dict, user_id: str
) -> ResourceSnapshot | None:
    """Capture the current state of the resource targeted by a high-risk tool.

    Returns None if the tool doesn't target a specific hashable resource.
    """
    # File mutation tools
    if tool_name in ("write_file", "delete_file", "move_file", "rename_file"):
        target_path = args.get("path") or args.get("file_path") or args.get("target")
        if not target_path:
            return None
        # Resolve under user workspace
        from xoai.workspace.service import get_user_workspace

        workspace = get_user_workspace(user_id)
        full_path = os.path.join(workspace, target_path.lstrip("/"))
        content_hash = compute_file_hash(full_path)
        return ResourceSnapshot(
            resource_type="file",
            resource_key=full_path,
            content_hash=content_hash,
        )

    # Shell execution — hash the workspace directory listing as a coarse state check
    if tool_name == "execute_command":
        from xoai.workspace.service import get_user_workspace

        workspace = get_user_workspace(user_id)
        try:
            listing = sorted(os.listdir(workspace))
            content_hash = compute_content_hash("|".join(listing))
        except OSError:
            content_hash = ""
        return ResourceSnapshot(
            resource_type="state",
            resource_key=workspace,
            content_hash=content_hash,
        )

    return None


async def verify_resource_unchanged(snapshot: ResourceSnapshot) -> tuple[bool, str]:
    """Re-check the resource hash and return (unchanged, reason)."""
    if snapshot.resource_type == "file":
        current_hash = compute_file_hash(snapshot.resource_key)
        if current_hash != snapshot.content_hash:
            return False, (
                f"File '{snapshot.resource_key}' was modified during the verification window. "
                f"Expected hash {snapshot.content_hash[:16]}…, got {current_hash[:16]}…"
            )
        return True, "Resource unchanged."

    if snapshot.resource_type == "state":
        try:
            listing = sorted(os.listdir(snapshot.resource_key))
            current_hash = compute_content_hash("|".join(listing))
        except OSError:
            return False, f"Cannot read state for '{snapshot.resource_key}'."
        if current_hash != snapshot.content_hash:
            return False, (
                f"Workspace state changed during the verification window. "
                f"Expected hash {snapshot.content_hash[:16]}…, got {current_hash[:16]}…"
            )
        return True, "State unchanged."

    return True, "No resource tracking for this type."


async def persist_proposal(proposal: ConsensusProposal) -> str:
    """Persist a consensus proposal to the database for audit trail."""
    db = get_db()
    doc = {
        "proposal_id": proposal.proposal_id,
        "acting_agent": proposal.acting_agent,
        "tool_name": proposal.tool_name,
        "args": proposal.args,
        "user_id": proposal.user_id,
        "conversation_id": proposal.conversation_id,
        "status": proposal.status,
        "verifier_feedback": proposal.verifier_feedback,
        "created_at": proposal.created_at,
    }
    if proposal.resource_snapshot:
        doc["resource_snapshot"] = {
            "resource_type": proposal.resource_snapshot.resource_type,
            "resource_key": proposal.resource_snapshot.resource_key,
            "content_hash": proposal.resource_snapshot.content_hash,
            "captured_at": proposal.resource_snapshot.captured_at,
        }
    result = await db.consensus_proposals.insert_one(doc)
    return str(result.inserted_id)


async def update_proposal_status(
    proposal_id: str,
    status: str,
    verifier_feedback: str = "",
) -> None:
    """Update the status of a consensus proposal."""
    db = get_db()
    await db.consensus_proposals.update_one(
        {"proposal_id": proposal_id},
        {
            "$set": {
                "status": status,
                "verifier_feedback": verifier_feedback,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
