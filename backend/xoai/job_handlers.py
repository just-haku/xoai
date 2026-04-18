from __future__ import annotations

from xoai.agents.memory import compact_engrams
from xoai.agents.supervisor import generate_auto_title
from xoai.auth.service import send_verification_email
from xoai.channels.manager import load_all_tenant_bots
from xoai.jobs import job_manager
from xoai.storage_gc import run_storage_gc
from xoai.tickets.service import agent_0_triage


async def send_verification_email_job(payload: dict) -> None:
    ok = await send_verification_email(
        payload["email"],
        payload["code_or_link"],
        subject=payload.get("subject", "XOAI Verification"),
    )
    if not ok:
        raise RuntimeError("Email delivery failed")


async def auto_title_job(payload: dict) -> None:
    await generate_auto_title(payload["chat_id"], payload["first_msg"])


async def ticket_triage_job(payload: dict) -> None:
    await agent_0_triage(payload["ticket_id"])


async def restore_tenant_bots_job(payload: dict) -> None:
    await load_all_tenant_bots()


async def storage_gc_job(payload: dict) -> None:
    await run_storage_gc(dry_run=payload.get("dry_run", False))


async def engram_compaction_job(payload: dict) -> None:
    """Run the engram compaction pipeline to summarize stale threads."""
    await compact_engrams(
        stale_days=payload.get("stale_days", 7),
        batch_size=payload.get("batch_size", 50),
    )


def register_job_handlers() -> None:
    job_manager.register_handler("verification_email", send_verification_email_job)
    job_manager.register_handler("auto_title", auto_title_job)
    job_manager.register_handler("ticket_triage", ticket_triage_job)
    job_manager.register_handler("restore_tenant_bots", restore_tenant_bots_job)
    job_manager.register_handler("storage_gc", storage_gc_job)
    job_manager.register_handler("engram_compaction", engram_compaction_job)
