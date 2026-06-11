from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


SourceId = Literal[
  "governance_primitives",
  "project_spec",
  "known_failures",
  "open_decisions",
  "active_implementation_plan",
  "active_implementation_tracker",
]

StaticSchemaId = Literal[
  "governance_primitives",
  "project_spec",
  "known_failures",
  "open_decisions",
  "implementation_plan",
  "implementation_tracker",
]

DocumentAuthority = Literal[
  "invariant_authority",
  "failure_evidence",
  "operational_state",
]


class StaticContextPacketMetadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  document_id: Literal["static_context_packet.json"]
  title: Literal["Static Context Packet"]
  purpose: Literal["Compiled static authority and operational context from StaticContextPacketManifest."]
  source_format: Literal["json"]
  document_authority: Literal["generated_artifact"]


class MissingSourceEntry(BaseModel):
  model_config = ConfigDict(extra="forbid")

  source_id: SourceId
  schema_id: StaticSchemaId
  document_authority: DocumentAuthority
  effect: Literal[
    "blocks_compilation",
    "recorded_absent"
    ]


class InvalidSourceEntry(BaseModel):
  model_config = ConfigDict(extra="forbid")

  source_id: SourceId
  schema_id: StaticSchemaId
  document_authority: DocumentAuthority
  effect: Literal[
    "blocks_compilation",
    "excluded_from_packet"
    ]


class SourceCoverageEntry(BaseModel):
  model_config = ConfigDict(extra="forbid")

  source_id: SourceId
  schema_id: StaticSchemaId
  document_authority: DocumentAuthority
  status: MissingSourceEntry | InvalidSourceEntry | Literal[
    "included",
    "skipped"
    ]
  resolved_path: str | None
  basis: list[str] = Field(default_factory=list)


class StaticContextPacket(BaseModel):
  model_config = ConfigDict(extra="forbid")

  metadata: StaticContextPacketMetadata

  governance_primitives: dict
  project_spec: dict
  known_failures: dict
  open_decisions: dict
  active_implementation_plan: dict | None = None
  active_implementation_tracker: dict | None = None

  source_coverage: list[SourceCoverageEntry]
  missing_sources: list[MissingSourceEntry] = Field(default_factory=list)
  invalid_sources: list[InvalidSourceEntry] = Field(default_factory=list)
