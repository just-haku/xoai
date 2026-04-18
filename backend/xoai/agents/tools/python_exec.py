"""Python code execution tool — routes through the sandbox runner for
zero-trust containerized execution.

The tool writes a job spec to the sandbox spool directory, waits for the
sandbox-runner container to process it, and returns bounded stdout/stderr.
"""

from __future__ import annotations

import logging

from xoai.metrics import metrics
from xoai.sandbox.executor import (
    NETWORK_ALLOWLISTED,
    NETWORK_DISABLED,
    submit_sandbox_job,
)

logger = logging.getLogger("xoai.agents.tools.python_exec")

MAX_CODE_LENGTH = 100_000


async def execute_python_code(
    user_id: str,
    code: str,
    timeout: int = 60,
    network_policy: str = NETWORK_DISABLED,
) -> str:
    """Execute Python code inside the isolated sandbox container.

    Args:
        user_id: Owner of the execution context.
        code: Python source code to execute.
        timeout: Maximum execution time in seconds (capped at 120s).
        network_policy: ``network_disabled`` (default) or ``network_allowlisted``.

    Returns:
        Bounded stdout/stderr from execution, or an error message.
    """
    if not code or not code.strip():
        return "Error: empty code."

    if len(code) > MAX_CODE_LENGTH:
        return f"Error: code exceeds maximum length ({MAX_CODE_LENGTH} chars)."

    if network_policy not in (NETWORK_DISABLED, NETWORK_ALLOWLISTED):
        network_policy = NETWORK_DISABLED

    timeout = min(max(timeout, 1), 120)

    try:
        result = await submit_sandbox_job(
            code=code,
            user_id=user_id,
            language="python",
            timeout=timeout,
            network_policy=network_policy,
        )

        metrics.incr("tools.python_exec.executed")

        stdout = result.get("stdout", "").strip()
        stderr = result.get("stderr", "").strip()

        if result.get("timed_out"):
            metrics.incr("tools.python_exec.timeout")
            return f"Error: execution timed out after {timeout}s."

        exit_code = result.get("exit_code", -1)
        output_parts = []
        if stdout:
            output_parts.append(stdout)
        if stderr:
            output_parts.append(f"[stderr]\n{stderr}")
        if not output_parts:
            output_parts.append(f"Process exited with code {exit_code}.")

        return "\n".join(output_parts)

    except Exception as exc:
        metrics.incr("tools.python_exec.failed")
        logger.exception("Sandbox execution failed", extra={"user_id": user_id})
        return f"Error: sandbox execution failed: {exc}"
