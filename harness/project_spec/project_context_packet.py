from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Metadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  document_id: Literal["project_context_packet.json"]
  title: Literal["Project Context Packet"]
  purpose: Literal["Provides the artifact for model call."]
  source_format: Literal["json"]
  document_authority: Literal["generated_artifact"]


class Task(BaseModel):
  model_config = ConfigDict(extra="forbid")

  # need to pull in the text that comes through the terminal from the user when invoking the harness.


class StaticContextPacket(BaseModel):
  model_config = ConfigDict(extra="forbid")

  # need to pull in contents listed in the StaticContextPacketManifest.


class GitContext(BaseModel):
  model_config = ConfigDict(extra="forbid")

  # need to pull in git context from repo.


class SupplementaryContextEntry(BaseModel):
  model_config = ConfigDict(extra="forbid")

  # need to pull in any additional context/attachments/documents from user (ie. screenshots, notes, repo files relating to implementation plan, etc.).


class SourceCoverageEntry(BaseModel):
  model_config = ConfigDict(extra="forbid")

  # need to pull in results from a script that reads what's been included in Task, StaticContextPacket, GitContext, and SupplementaryContextEntry.


class MissingSourceEntry(BaseModel):
  model_config = ConfigDict(extra="forbid")

  # need to pull in results from a script that cross references SourceCoverageEntry with expectations from StaticContextPacketManifest, and double checks there is a Task and GitContext present, as well as determines there is no funny business there, or in any included supplemental context if there is any.


class InvalidSourceEntry(BaseModel):
  model_config = ConfigDict(extra="forbid")

  # error results from cross reference with expectations in MissingSourceEntry.


class ProjectContextPacket(BaseModel):
  model_config = ConfigDict(extra="forbid")

  metadata: Metadata
  task: Task
  static_context_packet: StaticContextPacket
  git_context: GitContext
  supplementary_context: list[SupplementaryContextEntry]
  source_coverage: list[SourceCoverageEntry]
  missing_sources: list[MissingSourceEntry]
  invalid_sources: list[InvalidSourceEntry]





