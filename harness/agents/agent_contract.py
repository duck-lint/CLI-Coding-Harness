from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ProviderId = Literal["openai", "anthropic"]


class AgentMetadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  id: str = Field(min_length=1)
  agent_name: str = Field(min_length=1)
  document_authority: str = Field(min_length=1)


class AgentInputResolution(BaseModel):
  model_config = ConfigDict(extra="forbid")

  mode: Literal["paths", "globs", "all_admissible"]
  include_harness: bool = False
  paths: list[str] = Field(default_factory=list)
  globs: list[str] = Field(default_factory=list)
  max_file_bytes: int | None = Field(default=None, gt=0)
  max_total_bytes: int | None = Field(default=None, gt=0)

  @model_validator(mode="after")
  def validate_resolution_shape(self):
    if self.mode == "paths" and not self.paths:
      raise ValueError("paths mode requires at least one path.")

    if self.mode == "globs" and not self.globs:
      raise ValueError("globs mode requires at least one glob.")

    if self.mode == "all_admissible" and (self.paths or self.globs):
      raise ValueError(
        "all_admissible mode must not declare explicit paths or globs."
      )

    return self


class AgentInputPolicyEntry(BaseModel):
  model_config = ConfigDict(extra="forbid")

  input_id: str = Field(min_length=1)
  required: bool
  schema_ref: str = Field(min_length=1)
  resolution: AgentInputResolution | None = None


class AgentOutputPolicyEntry(BaseModel):
  model_config = ConfigDict(extra="forbid")

  output_id: str = Field(min_length=1)
  required: bool
  schema_ref: str = Field(min_length=1)


class AgentContract(BaseModel):
  model_config = ConfigDict(extra="forbid")

  schema_ref: str = Field(..., alias="$schema", min_length=1)
  metadata: AgentMetadata
  provider: ProviderId
  model: str = Field(min_length=1)
  instruction_contract: dict[str, Any]
  agent_input_policy: list[AgentInputPolicyEntry]
  agent_output_policy: list[AgentOutputPolicyEntry]
