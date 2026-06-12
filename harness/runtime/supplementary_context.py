from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SupplementaryContextEntry(BaseModel):
  model_config = ConfigDict(extra="forbid")

  source_id: str
  source_type: Literal[
    "user_note",
    "file",
    "attachment",
    "manual_context",
    "static_context_packet",
    "repo_snapshot_packet",
  ]
  content: str | dict | list
  included: bool = True
  basis: list[str] = Field(default_factory=list)
