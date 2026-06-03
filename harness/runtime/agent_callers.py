from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any

from harness.contracts import ProjectManagerReport
from harness.runtime.role_loader import RoleConfig


async def call_project_manager(role: RoleConfig, context_packet_json: str) -> ProjectManagerReport:
    try:
        from agents import Agent, Runner
    except ImportError as exc:
        raise RuntimeError(
            "The OpenAI Agents SDK is not installed. Run `python -m pip install -e .`."
        ) from exc

    context_budget = _context_budget(role)
    agent = Agent(
        name=role.name,
        instructions=_render_agent_instructions(role),
        model=role.model,
        model_settings=_build_model_settings(context_budget),
        output_type=ProjectManagerReport,
        tools=[],
        handoffs=[],
    )
    result = await Runner.run(agent, context_packet_json, max_turns=1)
    return _validate_final_output(result.final_output)


def _context_budget(role: RoleConfig) -> dict[str, int | str]:
    policy = role.runtime_budget
    return {
        "max_context_packet_tokens": int(policy.get("max_context_packet_tokens", 0)),
        "reserved_output_tokens": int(policy.get("reserved_output_tokens", 0)),
        "oversize_strategy": str(policy.get("oversize_strategy", "fail_or_batch")),
        "truncation": str(policy.get("truncation", "disabled")),
    }


def _build_model_settings(context_budget: dict[str, int | str]):
    try:
        from agents import ModelSettings
    except ImportError as exc:  # pragma: no cover - mirrors SDK availability guard
        raise RuntimeError(
            "The OpenAI Agents SDK is not installed. Run `python -m pip install -e .`."
        ) from exc

    truncation = context_budget["truncation"]
    if truncation not in {"disabled", "auto"}:
        raise ValueError(f"Unsupported truncation setting: {truncation}")

    return ModelSettings(
        max_tokens=int(context_budget["reserved_output_tokens"]),
        truncation=truncation,  # type: ignore[arg-type]
    )


@dataclass(frozen=True)
class EffectiveInstructionContract:
    role_instructions: dict[str, Any]
    source_coverage_requirements: dict[str, Any]
    token_budget_constraints: dict[str, Any]
    return_contract_requirements: dict[str, Any]


def build_effective_instruction_contract(role: RoleConfig) -> EffectiveInstructionContract:
    context_budget = _context_budget(role)
    return EffectiveInstructionContract(
        role_instructions=role.instructions_payload,
        source_coverage_requirements={
            "required": True,
            "entry_shape": {
                "source_id": "string",
                "used": "boolean",
                "claims_supported": ["string"],
                "reason": "string|null",
            },
            "used_claims_requirement": [
                "If used is true, claims_supported must be non-empty.",
                "If used is false, reason must be provided and claims_supported must be empty.",
            ],
        },
        token_budget_constraints={
            "max_context_packet_tokens": int(context_budget["max_context_packet_tokens"]),
            "reserved_output_tokens": int(context_budget["reserved_output_tokens"]),
            "oversize_strategy": context_budget["oversize_strategy"],
            "truncation": context_budget["truncation"],
            "truncation_must_be_disabled": True,
            "context_budget_must_be_enforced_before_call": True,
            "oversize_strategy_behavior": "fail_fast_until_batch_support_exists",
        },
        return_contract_requirements={
            "schema_path": str(role.return_contract.schema_path),
            "schema_title": role.return_contract.schema.get("title"),
            "required_fields": role.return_contract.schema.get("required", []),
            "returned_object_must_validate_schema": True,
            "source_coverage_required": "source_coverage"
            in role.return_contract.schema.get("required", []),
        },
    )


def _render_agent_instructions(role: RoleConfig) -> str:
    contract_json = json.dumps(
        asdict(build_effective_instruction_contract(role)),
        indent=2,
        ensure_ascii=False,
    )
    return "\n\n".join(
        [
            "The JSON object below is the complete effective instruction contract.",
            contract_json,
        ]
    )


def _validate_final_output(final_output: Any) -> ProjectManagerReport:
    if isinstance(final_output, ProjectManagerReport):
        return final_output
    if isinstance(final_output, str):
        return ProjectManagerReport.model_validate_json(final_output)
    return ProjectManagerReport.model_validate(final_output)
