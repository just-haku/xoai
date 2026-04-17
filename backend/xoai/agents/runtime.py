"""Query runtime: builds execution plans, runs nodes, and records experience."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from pydantic import ValidationError

from xoai.agents.base import BaseAgent
from xoai.agents.experience import (
    append_node_event,
    complete_node,
    finalize_query_run,
    record_node_start,
    start_query_run,
)
from xoai.agents.llm_pool import get_agent_config, get_user_agent_key
from xoai.agents.memory import get_conversation_messages, save_message
from xoai.agents.tool_registry import (
    create_admin_registry,
    create_user_registry,
    inject_mcp_tools,
)
from xoai.agents.topology import ExecutionNode, VerifierResult, build_execution_plan
from xoai.prompts.manager import get_runtime_prompt

logger = logging.getLogger("xoai.agents.runtime")

PASSING_VERIFIER_REASON_CODES = {"valid", "passed", "no_issue"}
VERIFIER_JSON_CONTRACT = (
    "\n\nVerifier output contract:\n"
    "Return only a strict JSON object with exactly these fields:\n"
    '{"is_valid": boolean, "reason_code": string, "feedback": string}\n'
    "Use is_valid=true only when the verified node fully satisfies the user request. "
    "Use a concise snake_case reason_code such as valid, implementation_defect, test_failure, "
    "regression, incomplete, unsafe, or invalid_verifier_output."
)


async def run_query(
    user: dict,
    message: str,
    conversation_id: str,
    channel: str = "web",
) -> AsyncIterator[dict]:
    history = await get_conversation_messages(conversation_id, limit=20)
    await save_message(conversation_id, "user", message, user_id=user["id"], channel_metadata={"channel": channel})

    plan = build_execution_plan(user, message, channel)
    query_id = await start_query_run(
        user=user,
        conversation_id=conversation_id,
        channel=channel,
        query=message,
        plan=plan.to_dict(),
    )

    yield {"type": "query_plan", "query_id": query_id, "plan": plan.to_dict()}

    node_outputs: dict[str, str] = {}
    node_statuses: dict[str, str] = {}
    node_failures: dict[str, str] = {}
    verifier_results: dict[str, VerifierResult] = {}
    retry_counts: dict[str, int] = {}
    final_output = ""
    failure_reason: str | None = None
    pending = {node.id: node for node in plan.nodes}

    while pending:
        ready = [
            node for node in pending.values()
            if all(dep in node_statuses for dep in node.depends_on)
        ]
        if not ready:
            failure_reason = failure_reason or "Execution plan stalled with unresolved dependencies."
            break

        batch = _select_batch(ready)
        event_queue: asyncio.Queue = asyncio.Queue()
        tasks = [
            asyncio.create_task(
                _execute_node(
                    query_id=query_id,
                    user=user,
                    node=node,
                    conversation_id=conversation_id,
                    original_message=message,
                    node_outputs=node_outputs,
                    node_statuses=node_statuses,
                    node_failures=node_failures,
                    verifier_results=verifier_results,
                    retry_counts=retry_counts,
                    history=history,
                    event_queue=event_queue,
                )
            )
            for node in batch
        ]

        completed_tasks = 0
        while completed_tasks < len(tasks):
            event = await event_queue.get()
            if event["type"] == "__node_done__":
                completed_tasks += 1
                continue
            yield event

        results = await asyncio.gather(*tasks)
        for node, result in zip(batch, results):
            pending.pop(node.id, None)
            node_statuses[node.id] = result["status"]
            node_outputs[node.id] = result["output"]
            if result.get("error"):
                node_failures[node.id] = result["error"]
            if node.branch_type == "verifier":
                verifier_result = result.get("verifier_result")
                if verifier_result:
                    verifier_results[node.verifier_for or node.id] = verifier_result

            if result["status"] == "completed":
                if node.branch_type != "verifier" and result["output"].strip():
                    final_output = result["output"]
                continue

            if node.branch_type == "verifier":
                continue

            if not _has_retry_path(plan.nodes, node.id):
                failure_reason = result.get("error") or failure_reason or f"Node '{node.id}' failed."
                pending.clear()
                break

    await finalize_query_run(
        query_id=query_id,
        final_output=final_output,
        status="failed" if failure_reason else "completed",
        failure_reason=failure_reason,
    )


def _compose_node_input(original_message: str, node: ExecutionNode, node_outputs: dict[str, str]) -> str:
    prior_outputs = [node_outputs[node_id] for node_id in node.depends_on if node_outputs.get(node_id)]
    if not prior_outputs:
        return original_message
    context = "\n\n".join(prior_outputs[-2:])
    return (
        f"Original user request:\n{original_message}\n\n"
        f"Prior node context:\n{context}\n\n"
        f"Current node objective: {node.action}"
    )


def _with_verifier_contract(node: ExecutionNode, node_input: str) -> str:
    if node.branch_type != "verifier":
        return node_input
    return f"{node_input}{VERIFIER_JSON_CONTRACT}"


async def _build_node_stream(
    user: dict,
    node: ExecutionNode,
    conversation_id: str,
    node_input: str,
    history: list[dict],
):
    config = await _get_agent_config_for_node(user, node)
    if not config:
        return {"type": "error", "message": f"No configuration found for role '{node.role}'."}

    registry = await _get_registry_for_node(user, node)
    agent = BaseAgent(
        _display_name(node.role),
        config,
        await get_runtime_prompt(node.prompt_name, role=node.role),
        tools=registry,
    )
    return agent.chat(user["id"], conversation_id, node_input, history)


async def _get_agent_config_for_node(user: dict, node: ExecutionNode) -> dict | None:
    if node.role == "architect":
        return await get_agent_config("agent_1")
    if node.role == "executor":
        return await get_agent_config("agent_2")
    if node.role == "supervisor":
        return await get_agent_config("agent_0")
    if node.role == "user_agent":
        return await get_user_agent_key(user["id"])
    return None


async def _get_registry_for_node(user: dict, node: ExecutionNode):
    if node.role == "architect":
        reg = create_admin_registry(read_only=True)
        await inject_mcp_tools(reg, user_id=user["id"], role="admin")
        return reg
    if node.role == "executor":
        reg = create_admin_registry()
        await inject_mcp_tools(reg, user_id=user["id"], role="admin")
        return reg
    if node.role == "user_agent":
        reg = create_user_registry()
        await inject_mcp_tools(reg, user_id=user["id"], role="user")
        return reg
    return None


def _display_name(role: str) -> str:
    return {
        "architect": "Agent 1",
        "executor": "Agent 2",
        "supervisor": "Agent 0",
        "user_agent": "UserAgent",
    }.get(role, role)


def _select_batch(ready: list[ExecutionNode]) -> list[ExecutionNode]:
    parallel_group = next((node.parallel_group for node in ready if node.parallel_group), None)
    if parallel_group:
        return [node for node in ready if node.parallel_group == parallel_group]
    return [ready[0]]


def _has_retry_path(nodes: list[ExecutionNode], node_id: str) -> bool:
    return any(node.retry_of == node_id for node in nodes)


def _should_run_retry(
    node: ExecutionNode,
    node_statuses: dict[str, str],
    node_failures: dict[str, str],
    verifier_results: dict[str, VerifierResult],
    retry_counts: dict[str, int],
) -> bool:
    target = node.retry_of or ""
    if retry_counts.get(target, 0) >= 1:
        return False
    if node_failures.get(target):
        retry_counts[target] = retry_counts.get(target, 0) + 1
        return True
    verifier_result = verifier_results.get(target)
    if verifier_result and _reason_code_requests_retry(verifier_result.reason_code):
        retry_counts[target] = retry_counts.get(target, 0) + 1
        return True
    if any(node_statuses.get(dep) == "failed" for dep in node.depends_on):
        retry_counts[target] = retry_counts.get(target, 0) + 1
        return True
    return False


def _reason_code_requests_retry(reason_code: str) -> bool:
    return reason_code.strip().lower() not in PASSING_VERIFIER_REASON_CODES


def _parse_verifier_result(output: str, error: str | None = None) -> VerifierResult:
    if error:
        return VerifierResult(is_valid=False, reason_code="runtime_error", feedback=error)

    try:
        payload = _extract_json_object(output)
        result = VerifierResult.model_validate(payload)
    except (ValueError, TypeError, ValidationError) as exc:
        return VerifierResult(
            is_valid=False,
            reason_code="invalid_verifier_output",
            feedback=f"Verifier did not return the required JSON contract: {exc}",
        )

    reason_code = result.reason_code.strip().lower()
    if result.is_valid and _reason_code_requests_retry(reason_code):
        return VerifierResult(
            is_valid=False,
            reason_code="inconsistent_verifier_output",
            feedback=(
                "Verifier returned is_valid=true with a failing reason_code. "
                f"Original feedback: {result.feedback}"
            ),
        )
    if not result.is_valid and not _reason_code_requests_retry(reason_code):
        return VerifierResult(
            is_valid=False,
            reason_code="verification_failed",
            feedback=result.feedback,
        )
    return VerifierResult(is_valid=result.is_valid, reason_code=reason_code, feedback=result.feedback)


def _extract_json_object(output: str) -> dict:
    stripped = output.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("No JSON object found in verifier output.")
        data = json.loads(stripped[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("Verifier output must be a JSON object.")
    return data


async def _execute_node(
    *,
    query_id: str,
    user: dict,
    node: ExecutionNode,
    conversation_id: str,
    original_message: str,
    node_outputs: dict[str, str],
    node_statuses: dict[str, str],
    node_failures: dict[str, str],
    verifier_results: dict[str, VerifierResult],
    retry_counts: dict[str, int],
    history: list[dict],
    event_queue: asyncio.Queue,
) -> dict:
    if node.branch_type == "retry" and not _should_run_retry(
        node,
        node_statuses=node_statuses,
        node_failures=node_failures,
        verifier_results=verifier_results,
        retry_counts=retry_counts,
    ):
        node_input = _compose_node_input(original_message, node, node_outputs)
        await record_node_start(query_id, node.to_dict(), node_input)
        await complete_node(query_id, node.id, "", status="skipped")
        await event_queue.put({
            "type": "node_skipped",
            "query_id": query_id,
            "node_id": node.id,
            "reason": "retry_not_needed",
        })
        await event_queue.put({"type": "__node_done__", "node_id": node.id})
        return {"status": "skipped", "output": "", "error": None, "verifier_result": None}

    node_input = _with_verifier_contract(node, _compose_node_input(original_message, node, node_outputs))
    if node.branch_type == "retry" and node.retry_of:
        verifier_result = verifier_results.get(node.retry_of)
        retry_context = node_failures.get(node.retry_of)
        if verifier_result:
            retry_context = f"{verifier_result.reason_code}: {verifier_result.feedback}"
        retry_context = retry_context or "Verifier requested retry."
        node_input = (
            f"{node_input}\n\nRetry target: {node.retry_of}\n"
            f"Retry reason: {retry_context}\n"
            "Revise the previous result and address the failure directly."
        )

    await record_node_start(query_id, node.to_dict(), node_input)
    await event_queue.put({"type": "node_start", "query_id": query_id, "node": node.to_dict()})

    stream = await _build_node_stream(user, node, conversation_id, node_input, history)
    node_output = ""
    node_error = None

    if not hasattr(stream, "__aiter__"):
        node_output = str(stream)
        event = {"type": "content", "content": node_output, "node_id": node.id}
        await append_node_event(query_id, node.id, event)
        await event_queue.put(event)
    else:
        async for chunk in stream:
            if chunk.get("type") == "agent_instance":
                await event_queue.put(chunk)
                continue

            enriched = dict(chunk)
            enriched.setdefault("node_id", node.id)
            if chunk.get("type") == "content":
                node_output += chunk.get("content", "")
            elif chunk.get("type") == "error":
                node_error = chunk.get("message", "Unknown node error")

            await append_node_event(query_id, node.id, enriched)
            await event_queue.put(enriched)

    verifier_result = _parse_verifier_result(node_output, node_error) if node.branch_type == "verifier" else None
    verdict_failed = bool(verifier_result and _reason_code_requests_retry(verifier_result.reason_code))
    status = "failed" if node_error or verdict_failed else "completed"
    final_error = node_error or (
        f"Verifier rejected output: {verifier_result.reason_code}" if verdict_failed and verifier_result else None
    )

    await complete_node(
        query_id,
        node.id,
        node_output,
        status=status,
        structured_output=verifier_result.model_dump() if verifier_result else None,
    )
    await event_queue.put({"type": "node_end", "query_id": query_id, "node_id": node.id, "status": status})
    await event_queue.put({"type": "__node_done__", "node_id": node.id})
    return {
        "status": status,
        "output": node_output,
        "error": final_error,
        "verifier_result": verifier_result,
    }
