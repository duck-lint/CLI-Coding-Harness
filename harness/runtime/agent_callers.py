from __future__ import annotations

from typing import Any

from harness.contracts import ProjectManagerReport
from harness.runtime.role_loader import RoleConfig


async def call_project_manager(role: RoleConfig, context_packet: str) -> ProjectManagerReport:
    try:
        from agents import Agent, Runner
    except ImportError as exc:
        raise RuntimeError(
            "The OpenAI Agents SDK is not installed. Run `python -m pip install -e .`."
        ) from exc

    agent = Agent(
        name=role.name,
        instructions=_structured_instructions(role.instructions),
        model=role.model,
        output_type=ProjectManagerReport,
        tools=[],
        handoffs=[],
    )
    result = await Runner.run(agent, context_packet, max_turns=1)
    return _validate_final_output(result.final_output)


def _structured_instructions(base_instructions: str) -> str:
    return "\n\n".join(
        [
            base_instructions.strip(),
            "Return only a structured ProjectManagerReport matching the supplied output schema. "
            "Do not call tools, do not request shell access, and do not modify files.",
        ]
    )


def _validate_final_output(final_output: Any) -> ProjectManagerReport:
    if isinstance(final_output, ProjectManagerReport):
        return final_output
    if isinstance(final_output, str):
        return ProjectManagerReport.model_validate_json(final_output)
    return ProjectManagerReport.model_validate(final_output)
