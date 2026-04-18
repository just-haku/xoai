"""Sandbox executor client — submits jobs to the sandbox runner via spool
directory and polls for results.

Used by the agent tool layer to execute user code in an isolated container.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path

from xoai.config import settings

logger = logging.getLogger("xoai.sandbox.executor")

SPOOL_ROOT = Path(os.environ.get("SANDBOX_SPOOL", "/app/storage/_sandbox_spool"))
PENDING_DIR = SPOOL_ROOT / "pending"
DONE_DIR = SPOOL_ROOT / "done"

POLL_INTERVAL = 0.3
MAX_POLL_SECONDS = 130

# Network egress policy constants
NETWORK_DISABLED = "network_disabled"
NETWORK_ALLOWLISTED = "network_allowlisted"

ALLOWED_EGRESS_DOMAINS = [
    "api.openai.com",
    "generativelanguage.googleapis.com",
    "api.anthropic.com",
    "pypi.org",
    "files.pythonhosted.org",
]


def _ensure_spool_dirs() -> None:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)


async def submit_sandbox_job(
    *,
    code: str,
    user_id: str,
    language: str = "python",
    timeout: int = 60,
    network_policy: str = NETWORK_DISABLED,
) -> dict:
    """Submit a code execution job to the sandbox runner and wait for the result.

    Returns a dict with keys: job_id, exit_code, stdout, stderr, timed_out.
    """
    _ensure_spool_dirs()

    job_id = f"{user_id[:8]}_{uuid.uuid4().hex[:12]}"
    spec = {
        "job_id": job_id,
        "language": language,
        "code": code,
        "timeout": timeout,
        "user_id": user_id,
        "network_policy": network_policy,
        "allowed_egress_domains": ALLOWED_EGRESS_DOMAINS if network_policy == NETWORK_ALLOWLISTED else [],
    }

    spec_file = PENDING_DIR / f"{job_id}.json"
    spec_file.write_text(json.dumps(spec), encoding="utf-8")

    logger.info("Submitted sandbox job %s (network=%s)", job_id, network_policy)

    # Poll for result
    result_file = DONE_DIR / f"{job_id}.json"
    elapsed = 0.0

    while elapsed < MAX_POLL_SECONDS:
        if result_file.exists():
            try:
                result = json.loads(result_file.read_text(encoding="utf-8"))
                result_file.unlink(missing_ok=True)
                return result
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Corrupt sandbox result for %s: %s", job_id, exc)
                result_file.unlink(missing_ok=True)
                return {
                    "job_id": job_id,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Corrupt result: {exc}",
                    "timed_out": False,
                }

        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    # Timeout — clean up pending spec
    spec_file.unlink(missing_ok=True)
    logger.warning("Sandbox job %s timed out after %ss poll wait", job_id, MAX_POLL_SECONDS)
    return {
        "job_id": job_id,
        "exit_code": -1,
        "stdout": "",
        "stderr": f"Sandbox job timed out after {MAX_POLL_SECONDS}s.",
        "timed_out": True,
    }


def get_network_profile_args(network_policy: str) -> dict:
    """Return Docker network arguments for the sandbox container based on policy.

    Used by orchestration tooling when dynamically launching sandbox containers.
    """
    if network_policy == NETWORK_DISABLED:
        return {"network_mode": "none"}
    elif network_policy == NETWORK_ALLOWLISTED:
        return {"network": "sandbox-egress"}
    return {"network_mode": "none"}
