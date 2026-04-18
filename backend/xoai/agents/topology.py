"""Execution topology models and template-based planner."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class VerifierResult(BaseModel):
    """Strict structured contract for verifier node output."""

    model_config = ConfigDict(extra="forbid")

    is_valid: StrictBool
    reason_code: str = Field(min_length=1)
    feedback: str = Field(min_length=1)


@dataclass
class ExecutionNode:
    id: str
    role: str
    action: str
    prompt_name: str
    tool_mode: str = "none"
    depends_on: list[str] = field(default_factory=list)
    branch_type: str = "primary"
    parallel_group: str | None = None
    retry_of: str | None = None
    verifier_for: str | None = None
    max_retries: int = 0
    entry_condition: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionPlan:
    topology_type: str
    intent_profile: str
    nodes: list[ExecutionNode]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_type": self.topology_type,
            "intent_profile": self.intent_profile,
            "nodes": [node.to_dict() for node in self.nodes],
            "metadata": self.metadata,
        }


def build_execution_plan(user: dict, message: str, channel: str = "web") -> ExecutionPlan:
    """Create a per-query execution plan from lightweight heuristics."""
    lowered = message.lower()
    user_role = user.get("role", "user")

    if user_role != "admin":
        return ExecutionPlan(
            topology_type="user_direct",
            intent_profile="user.personal_assistant",
            nodes=[
                ExecutionNode(
                    id="user_agent",
                    role="user_agent",
                    action="answer",
                    prompt_name="user_agent",
                    tool_mode="standard",
                )
            ],
            metadata={"channel": channel},
        )

    if _needs_clarification(lowered):
        return ExecutionPlan(
            topology_type="clarify_then_execute",
            intent_profile="admin.clarification",
            nodes=[
                ExecutionNode(
                    id="architect_clarify",
                    role="architect",
                    action="clarify",
                    prompt_name="architect",
                    tool_mode="read_only",
                    metadata={"phase": "clarify"},
                ),
                ExecutionNode(
                    id="executor_answer",
                    role="executor",
                    action="execute",
                    prompt_name="executor",
                    tool_mode="standard",
                    depends_on=["architect_clarify"],
                    metadata={"phase": "execute"},
                ),
            ],
            metadata={"channel": channel},
        )

    if any(keyword in lowered for keyword in ["verify", "review", "check", "audit", "test"]):
        return ExecutionPlan(
            topology_type="execute_then_verify_then_retry",
            intent_profile="admin.execution",
            nodes=[
                ExecutionNode(
                    id="executor",
                    role="executor",
                    action="execute",
                    prompt_name="executor",
                    tool_mode="standard",
                    max_retries=1,
                    metadata={"phase": "execute"},
                ),
                ExecutionNode(
                    id="architect_verify",
                    role="architect",
                    action="verify",
                    prompt_name="architect",
                    tool_mode="read_only",
                    depends_on=["executor"],
                    branch_type="verifier",
                    verifier_for="executor",
                    metadata={"phase": "verify", "output_schema": "VerifierResult"},
                ),
                ExecutionNode(
                    id="executor_retry",
                    role="executor",
                    action="retry",
                    prompt_name="executor",
                    tool_mode="standard",
                    depends_on=["architect_verify"],
                    branch_type="retry",
                    retry_of="executor",
                    entry_condition="verifier_failed_or_runtime_error",
                    metadata={"phase": "retry"},
                ),
            ],
            metadata={"channel": channel},
        )

    if any(keyword in lowered for keyword in ["compare", "investigate", "research", "find", "search"]):
        return ExecutionPlan(
            topology_type="research_parallel_compare_synthesize",
            intent_profile="admin.research",
            nodes=[
                ExecutionNode(
                    id="architect_research_primary",
                    role="architect",
                    action="research_primary",
                    prompt_name="architect",
                    tool_mode="read_only",
                    parallel_group="research",
                    metadata={"phase": "research"},
                ),
                ExecutionNode(
                    id="architect_research_secondary",
                    role="architect",
                    action="research_secondary",
                    prompt_name="architect",
                    tool_mode="read_only",
                    parallel_group="research",
                    metadata={"phase": "research"},
                ),
                ExecutionNode(
                    id="architect_compare",
                    role="architect",
                    action="compare",
                    prompt_name="architect",
                    tool_mode="read_only",
                    depends_on=["architect_research_primary", "architect_research_secondary"],
                    metadata={"phase": "compare"},
                ),
                ExecutionNode(
                    id="executor_synthesize",
                    role="executor",
                    action="synthesize",
                    prompt_name="executor",
                    tool_mode="standard",
                    depends_on=["architect_compare"],
                    metadata={"phase": "synthesize"},
                ),
            ],
            metadata={"channel": channel},
        )

    if any(keyword in lowered for keyword in ["plan", "design", "architect", "topology", "roadmap"]):
        return ExecutionPlan(
            topology_type="architect_parallel_research_then_execute",
            intent_profile="admin.architecture",
            nodes=[
                ExecutionNode(
                    id="architect",
                    role="architect",
                    action="plan",
                    prompt_name="architect",
                    tool_mode="read_only",
                    metadata={"phase": "plan"},
                ),
                ExecutionNode(
                    id="architect_research_constraints",
                    role="architect",
                    action="research_constraints",
                    prompt_name="architect",
                    tool_mode="read_only",
                    parallel_group="planning_research",
                    metadata={"phase": "research"},
                ),
                ExecutionNode(
                    id="architect_research_examples",
                    role="architect",
                    action="research_examples",
                    prompt_name="architect",
                    tool_mode="read_only",
                    parallel_group="planning_research",
                    metadata={"phase": "research"},
                ),
                ExecutionNode(
                    id="executor",
                    role="executor",
                    action="execute",
                    prompt_name="executor",
                    tool_mode="standard",
                    depends_on=["architect", "architect_research_constraints", "architect_research_examples"],
                    metadata={"phase": "execute"},
                ),
            ],
            metadata={"channel": channel},
        )

    return ExecutionPlan(
        topology_type="direct_answer",
        intent_profile="admin.general",
        nodes=[
            ExecutionNode(
                id="executor",
                role="executor",
                action="answer",
                prompt_name="executor",
                tool_mode="standard",
            )
        ],
        metadata={"channel": channel},
    )


def _needs_clarification(lowered: str) -> bool:
    ambiguous_markers = ["not sure", "maybe", "help me figure out", "unclear", "which should", "what should"]
    return "?" in lowered and any(marker in lowered for marker in ambiguous_markers)
