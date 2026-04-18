import pytest

from xoai.agents.runtime import _parse_verifier_result, _select_batch, _should_run_retry
from xoai.agents.topology import ExecutionNode, VerifierResult, build_execution_plan


def test_build_execution_plan_creates_parallel_research_template():
    plan = build_execution_plan({"role": "admin", "id": "u1"}, "Research and compare two options", "web")
    assert plan.topology_type == "research_parallel_compare_synthesize"
    parallel_nodes = [node for node in plan.nodes if node.parallel_group == "research"]
    assert len(parallel_nodes) == 2
    assert any(node.action == "compare" for node in plan.nodes)


def test_build_execution_plan_creates_verifier_retry_template():
    plan = build_execution_plan({"role": "admin", "id": "u1"}, "Review and verify this implementation", "web")
    verify_node = next(node for node in plan.nodes if node.branch_type == "verifier")
    retry_node = next(node for node in plan.nodes if node.branch_type == "retry")
    assert verify_node.verifier_for == "executor"
    assert retry_node.retry_of == "executor"
    assert retry_node.entry_condition == "verifier_failed_or_runtime_error"


def test_select_batch_prefers_parallel_group():
    nodes = [
        ExecutionNode(id="a", role="architect", action="r1", prompt_name="architect", parallel_group="research"),
        ExecutionNode(id="b", role="architect", action="r2", prompt_name="architect", parallel_group="research"),
        ExecutionNode(id="c", role="executor", action="execute", prompt_name="executor"),
    ]
    batch = _select_batch(nodes)
    assert [node.id for node in batch] == ["a", "b"]


def test_retry_runs_on_failed_executor():
    retry_node = ExecutionNode(
        id="executor_retry",
        role="executor",
        action="retry",
        prompt_name="executor",
        branch_type="retry",
        retry_of="executor",
    )
    retry_counts = {}
    should_run = _should_run_retry(
        retry_node,
        node_statuses={"executor": "failed"},
        node_failures={"executor": "runtime error"},
        verifier_results={},
        retry_counts=retry_counts,
    )
    assert should_run is True
    assert retry_counts["executor"] == 1


def test_retry_runs_on_structured_verifier_reason_code():
    retry_node = ExecutionNode(
        id="executor_retry",
        role="executor",
        action="retry",
        prompt_name="executor",
        branch_type="retry",
        retry_of="executor",
    )
    retry_counts = {}
    should_run = _should_run_retry(
        retry_node,
        node_statuses={"executor": "completed", "architect_verify": "failed"},
        node_failures={},
        verifier_results={
            "executor": VerifierResult(
                is_valid=False,
                reason_code="regression",
                feedback="The implementation regressed file loading.",
            )
        },
        retry_counts=retry_counts,
    )
    assert should_run is True
    assert retry_counts["executor"] == 1


def test_retry_skips_on_valid_structured_verifier_result():
    retry_node = ExecutionNode(
        id="executor_retry",
        role="executor",
        action="retry",
        prompt_name="executor",
        branch_type="retry",
        retry_of="executor",
    )
    retry_counts = {}
    should_run = _should_run_retry(
        retry_node,
        node_statuses={"executor": "completed", "architect_verify": "completed"},
        node_failures={},
        verifier_results={
            "executor": VerifierResult(
                is_valid=True,
                reason_code="valid",
                feedback="The implementation satisfies the request.",
            )
        },
        retry_counts=retry_counts,
    )
    assert should_run is False
    assert retry_counts == {}


def test_parse_verifier_result_requires_strict_json_contract():
    parsed = _parse_verifier_result(
        '{"is_valid": false, "reason_code": "test_failure", "feedback": "A test failed."}',
        None,
    )
    assert parsed.is_valid is False
    assert parsed.reason_code == "test_failure"
    assert parsed.feedback == "A test failed."

    invalid = _parse_verifier_result("The implementation has a regression and should retry.", None)
    assert invalid.is_valid is False
    assert invalid.reason_code == "invalid_verifier_output"


def test_verifier_result_rejects_extra_fields():
    with pytest.raises(Exception):
        VerifierResult(
            is_valid=True,
            reason_code="valid",
            feedback="ok",
            extra_field="not-allowed",
        )
