"""Sandbox runner — watches a spool directory for job specs, executes them
in a constrained subprocess, and writes bounded stdout/stderr back.

This module is designed to be the entrypoint inside a container launched with
``network_mode: none`` (or a restricted network profile).  The host writes a
JSON job spec into ``/sandbox/spool/pending/`` and the runner picks it up,
executes it, then writes results to ``/sandbox/spool/done/``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger("xoai.sandbox.runner")

SPOOL_ROOT = Path(os.environ.get("SANDBOX_SPOOL", "/sandbox/spool"))
PENDING_DIR = SPOOL_ROOT / "pending"
DONE_DIR = SPOOL_ROOT / "done"
SCRATCH_DIR = Path(os.environ.get("SANDBOX_SCRATCH", "/sandbox/scratch"))

MAX_TIMEOUT_SECONDS = 120
MAX_OUTPUT_BYTES = 8192
POLL_INTERVAL_SECONDS = 0.25


def _safe_env() -> dict[str, str]:
    """Return a scrubbed environment for subprocess execution."""
    return {
        "HOME": str(SCRATCH_DIR),
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }


def _execute_job(spec: dict) -> dict:
    """Execute a single job spec and return a result dict."""
    language = spec.get("language", "python")
    code = spec.get("code", "")
    timeout = min(int(spec.get("timeout", 60)), MAX_TIMEOUT_SECONDS)
    job_id = spec.get("job_id", "unknown")

    if language != "python":
        return {
            "job_id": job_id,
            "exit_code": 1,
            "stdout": "",
            "stderr": f"Unsupported language: {language}",
            "timed_out": False,
        }

    # Write code to a temp file in scratch
    script_path = SCRATCH_DIR / f"job_{job_id}.py"
    script_path.write_text(code, encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(SCRATCH_DIR),
            env=_safe_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = (result.stdout or "")[-MAX_OUTPUT_BYTES:]
        stderr = (result.stderr or "")[-MAX_OUTPUT_BYTES:]
        return {
            "job_id": job_id,
            "exit_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "job_id": job_id,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout}s.",
            "timed_out": True,
        }
    except Exception as exc:
        return {
            "job_id": job_id,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
        }
    finally:
        script_path.unlink(missing_ok=True)


def _poll_loop() -> None:
    """Main polling loop — watches PENDING_DIR for new job spec files."""
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Sandbox runner started, polling %s", PENDING_DIR)

    while True:
        for spec_file in sorted(PENDING_DIR.glob("*.json")):
            try:
                spec = json.loads(spec_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Bad job spec %s: %s", spec_file.name, exc)
                spec_file.unlink(missing_ok=True)
                continue

            job_id = spec.get("job_id", spec_file.stem)
            spec["job_id"] = job_id
            logger.info("Processing job %s", job_id)

            result = _execute_job(spec)

            result_file = DONE_DIR / f"{job_id}.json"
            result_file.write_text(json.dumps(result), encoding="utf-8")

            spec_file.unlink(missing_ok=True)
            logger.info("Job %s completed (exit=%s)", job_id, result["exit_code"])

        time.sleep(POLL_INTERVAL_SECONDS)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    _poll_loop()


if __name__ == "__main__":
    main()
