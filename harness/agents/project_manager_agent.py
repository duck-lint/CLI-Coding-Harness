from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from harness.agents.agent_contract import (
  AgentInputPolicyEntry,
  AgentOutputPolicyEntry,
  ProviderId,
)


class Metadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  id: Literal["project_manager.agent.json"]
  agent_name: Literal["Project Manager"]


class StatusSemantics(BaseModel):
  model_config = ConfigDict(extra="forbid")

  admissible: Literal["The task can proceed under current project and task authority; the frontier is open enough to name the next admissible move."]
  admissibility_blocked: Literal["The requested object-level transformation cannot proceed because required basis, context, or authority is missing; the frontier may still be open enough to name a diagnostic or unblock move."]
  rejected: Literal["The requested thesis or action conflicts with invariant project or harness authority; the frontier may still be open enough to name a correction, reclassification, or probe move."]
  needs_clarification: Literal["The task is ambiguous enough that user clarification is required; the frontier may still be open enough to name a clarification move."]


class ProjectManagerReportDerivationRules(BaseModel):
  model_config = ConfigDict(extra="forbid")

  evaluation_basis: str
  drift_checks: str
  next_step_recommendations: str
  repository_state: str
  status_semantics: StatusSemantics


class ReviewLenses(BaseModel):
  model_config = ConfigDict(extra="forbid")

  invariant_coverage: str
  task_coverage: str
  source_coverage_truthfulness: str
  conflict_visibility: str
  admissible_transformation_coverage: str
  surface_truthfulness: str
  evidence_quality: str
  fixture_truthfulness: str
  posture_concreteness: str
  thesis_attractor_discipline: str
  tension_selection: str
  frontier_selection: str
  optionality_preservation: str


class InstructionContract(BaseModel):
  model_config = ConfigDict(extra="forbid")

  role: str
  posture: str
  objective: str
  validity_conditions: list[str]
  project_manager_report_derivation_rules: ProjectManagerReportDerivationRules
  conduct_rules: list[str]
  review_lenses: ReviewLenses


class ProjectManagerOutputPolicyEntry(AgentOutputPolicyEntry):
  output_id: Literal["project_manager_report"]
  required: bool
  schema_ref: Literal["../contracts/ProjectManagerReport.schema.json"]


class ProjectManagerAgent(BaseModel):
  model_config = ConfigDict(extra="forbid")

  schema_ref: str = Field(..., alias='$schema')
  metadata: Metadata
  provider: ProviderId
  model: str = Field(min_length=1)
  instruction_contract: InstructionContract
  agent_input_policy: list[AgentInputPolicyEntry]
  agent_output_policy: list[ProjectManagerOutputPolicyEntry]
