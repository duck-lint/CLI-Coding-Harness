from __future__ import annotations

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

    agent = Agent(
        name=role.name,
        instructions=_render_agent_instructions(role),
        model=role.model,
        output_type=ProjectManagerReport,
        tools=[],
        handoffs=[],
    )
    result = await Runner.run(agent, context_packet_json, max_turns=1)
    return _validate_final_output(result.final_output)


def _render_agent_instructions(role: RoleConfig) -> str:
    instructions_json = json.dumps(role.instructions_payload, indent=2, ensure_ascii=False)
    return "\n\n".join(
        [
            "Use this agent contract as the authoritative instruction source.",
            instructions_json,
            "Return only a structured ProjectManagerReport that matches the configured return contract.",
        ]
    )


def _validate_final_output(final_output: Any) -> ProjectManagerReport:
    if isinstance(final_output, ProjectManagerReport):
        return final_output
    if isinstance(final_output, str):
        return ProjectManagerReport.model_validate_json(final_output)
    return ProjectManagerReport.model_validate(final_output)
