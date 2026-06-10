from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Metadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  id: Literal["project_context_packet.manifest.json"]
  name: Literal["Project Context Packet Manifest"]


class Source(BaseModel):
  model_config = ConfigDict(extra="forbid")

  source_id: Literal[
    "governance_primitives",
    "project_spec",
    "known_failures",
    "open_decisions",
    "active_implementation_plan",
    "active_implementation_tracker",
  ]

  scope: Literal[
    "harness_global",
    "target_repo",
  ]

  required: bool
  required_when: str | None = None

  document_authority: Literal[
    "invariant_authority",
    "failure_evidence",
    "operational_state",
  ]

  document: str | None = None
  document_glob: str | None = None

  schema_id: Literal[
    "governance_primitives",
    "project_spec",
    "known_failures",
    "open_decisions",
    "implementation_plan",
    "implementation_tracker",
  ]

  cardinality: Literal[
    "exactly_one",
    "zero_or_one",
    "zero_or_more",
    "one_or_more",
  ]

  @model_validator(mode="after")
  def enforce_document_reference_shape(self):
    has_document = self.document is not None
    has_glob = self.document_glob is not None

    if has_document == has_glob:
      raise ValueError(
        "Each manifest source must define exactly one of document or document_glob."
      )

    if self.document is not None and "*" in self.document:
      raise ValueError(
        "Use document_glob for glob patterns; document must be a single path."
      )

    return self

  @model_validator(mode="after")
  def enforce_required_cardinality_coherence(self):
    if self.required and self.cardinality in {"zero_or_one", "zero_or_more"}:
      raise ValueError(
        "A required source should not have a zero-allowed cardinality."
      )

    if not self.required and self.cardinality == "exactly_one" and self.required_when is None:
      raise ValueError(
        "An optional source with exactly_one cardinality needs required_when, "
        "or should use zero_or_one."
      )

    return self

  @model_validator(mode="after")
  def enforce_source_specific_contract(self):
    expected = SOURCE_CONTRACTS[self.source_id]

    for field_name, expected_value in expected.items():
      actual_value = getattr(self, field_name)

      if actual_value != expected_value:
        raise ValueError(
          f"{self.source_id}.{field_name} must be {expected_value!r}, "
          f"got {actual_value!r}."
        )

    return self

class ProjectContextPacketManifest(BaseModel):
  model_config = ConfigDict(extra="forbid")

  schema_ref: str = Field(..., alias="$schema")
  metadata: Metadata
  sources: list[Source]


SOURCE_CONTRACTS = {
    "governance_primitives": {
        "scope": "harness_global",
        "document_authority": "invariant_authority",
        "schema_id": "governance_primitives",
        "cardinality": "exactly_one",
    },
    "project_spec": {
        "scope": "target_repo",
        "document_authority": "invariant_authority",
        "schema_id": "project_spec",
        "cardinality": "exactly_one",
    },
    "known_failures": {
        "scope": "target_repo",
        "document_authority": "failure_evidence",
        "schema_id": "known_failures",
        "cardinality": "exactly_one",
    },
    "open_decisions": {
        "scope": "target_repo",
        "document_authority": "operational_state",
        "schema_id": "open_decisions",
        "cardinality": "exactly_one",
    },
    "active_implementation_plan": {
        "scope": "target_repo",
        "document_authority": "operational_state",
        "schema_id": "implementation_plan",
        "cardinality": "zero_or_one",
    },
    "active_implementation_tracker": {
        "scope": "target_repo",
        "document_authority": "operational_state",
        "schema_id": "implementation_tracker",
        "cardinality": "zero_or_one",
    },
}
