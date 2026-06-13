from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from harness.agents.agent_contract import AgentContract
from harness.project_spec.static_context_packet import StaticContextPacket
from harness.repo_snapshot.repo_snapshot_packet import RepoSnapshotPacket


class AgentContextPacketMetadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  document_id: Literal["agent_context_packet.json"]
  title: Literal["Agent Context Packet"]
  purpose: Literal[
    "Agent-specific context compiled from the selected agent input policy."
  ]
  source_format: Literal["json"]
  document_authority: Literal["compiled_runtime_artifact"]


class AgentContextInputCoverageEntry(BaseModel):
  model_config = ConfigDict(extra="forbid")

  input_id: str
  required: bool
  status: Literal["included", "missing", "invalid"]
  schema_ref: str | None = None
  basis: list[str] = Field(default_factory=list)


class AgentResolvedInputs(BaseModel):
  model_config = ConfigDict(extra="forbid")

  static_context_packet: StaticContextPacket | None = None
  repo_snapshot_packet: RepoSnapshotPacket | None = None


class AgentContextPacket(BaseModel):
  model_config = ConfigDict(extra="forbid")

  metadata: AgentContextPacketMetadata
  agent_contract: AgentContract
  resolved_inputs: AgentResolvedInputs
  input_coverage: list[AgentContextInputCoverageEntry] = Field(
    default_factory=list
  )
