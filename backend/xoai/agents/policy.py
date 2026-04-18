from __future__ import annotations

import json
import logging
import uuid
from collections import Counter
from dataclasses import dataclass, field

from pydantic import ValidationError

from xoai.agents.consensus import (
    ConsensusProposal,
    capture_resource_snapshot,
    persist_proposal,
    update_proposal_status,
    verify_resource_unchanged,
)
from xoai.agents.llm_pool import get_provider
from xoai.agents.topology import VerifierResult
from xoai.config import settings
from xoai.db.mongo import get_db
from xoai.prompts.manager import get_runtime_prompt

logger = logging.getLogger("xoai.agents.policy")

HIGH_RISK_CLASSES = {"mutating_high", "external_side_effect", "operator_sensitive"}
RETRIABLE_RESULT_PREFIX = "Error:"


@dataclass
class QueryBudget:
    max_steps: int = settings.query_max_tool_steps
    max_repeat_failures: int = settings.query_tool_failure_threshold
    failure_counts: Counter = field(default_factory=Counter)

    def record_failure(self, key: str) -> None:
        self.failure_counts[key] += 1

    def repeat_failures(self, key: str) -> int:
        return self.failure_counts[key]


async def get_agent_profile(agent_key: str | None = None, role: str | None = None) -> dict | None:
    db = get_db()
    query = {"enabled": {"$ne": False}}
    if agent_key:
        query["agent_key"] = agent_key
    if role:
        query["role"] = role
    return await db.agent_profiles.find_one(query)


async def enforce_high_risk_consensus(
    *,
    acting_agent: str,
    tool_name: str,
    args: dict,
    user_id: str,
    conversation_id: str,
) -> VerifierResult:
    """Full two-step idempotent consensus: capture hash → verify → commit guard."""

    # Step 1: Capture resource snapshot at proposal time
    snapshot = await capture_resource_snapshot(tool_name, args, user_id)

    proposal = ConsensusProposal(
        proposal_id=uuid.uuid4().hex,
        acting_agent=acting_agent,
        tool_name=tool_name,
        args=args,
        user_id=user_id,
        conversation_id=conversation_id,
        resource_snapshot=snapshot,
        status="pending",
    )
    await persist_proposal(proposal)

    # Step 2: Send to verifier agent
    profile = await get_agent_profile(role="architect")
    if not profile:
        await update_proposal_status(proposal.proposal_id, "rejected", "No verifier agent configured.")
        return VerifierResult(
            is_valid=False,
            reason_code="missing_verifier_agent",
            feedback="No enabled architect/verifier agent profile is configured.",
        )

    provider = await get_provider(profile)
    prompt = await get_runtime_prompt(
        "architect",
        role="architect",
    )

    resource_context = ""
    if snapshot:
        resource_context = (
            f"\nResource snapshot:\n"
            f"  type={snapshot.resource_type}\n"
            f"  key={snapshot.resource_key}\n"
            f"  hash={snapshot.content_hash[:32]}…\n"
        )

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                "Review the following high-risk tool execution proposal. "
                "Return only JSON using this contract: "
                '{"is_valid": boolean, "reason_code": string, "feedback": string}\n\n'
                f"acting_agent={acting_agent}\n"
                f"user_id={user_id}\n"
                f"conversation_id={conversation_id}\n"
                f"tool_name={tool_name}\n"
                f"args={json.dumps(args, sort_keys=True)}"
                f"{resource_context}"
            ),
        },
    ]

    try:
        response = await provider.chat(model=profile["model"], messages=messages)
        raw = (response or {}).get("content", "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]
        payload = json.loads(raw)
        result = VerifierResult.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
        logger.warning("Invalid verifier response for consensus", extra={"tool_name": tool_name, "error": str(exc)})
        await update_proposal_status(proposal.proposal_id, "rejected", f"Parse error: {exc}")
        return VerifierResult(
            is_valid=False,
            reason_code="invalid_verifier_response",
            feedback=f"Verifier response could not be parsed: {exc}",
        )
    except Exception as exc:
        logger.warning("Verifier consensus failed", extra={"tool_name": tool_name, "error": str(exc)})
        await update_proposal_status(proposal.proposal_id, "rejected", str(exc))
        return VerifierResult(
            is_valid=False,
            reason_code="verifier_runtime_error",
            feedback=str(exc),
        )

    if not result.is_valid:
        await update_proposal_status(proposal.proposal_id, "rejected", result.feedback)
        return result

    # Step 3: Idempotent commit guard — re-check resource hash before committing
    if snapshot:
        unchanged, reason = await verify_resource_unchanged(snapshot)
        if not unchanged:
            await update_proposal_status(proposal.proposal_id, "stale", reason)
            logger.warning(
                "Consensus commit rejected: resource changed during verification window",
                extra={"proposal_id": proposal.proposal_id, "reason": reason},
            )
            return VerifierResult(
                is_valid=False,
                reason_code="resource_state_conflict",
                feedback=reason,
            )

    await update_proposal_status(proposal.proposal_id, "committed", result.feedback)
    return result
