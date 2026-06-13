from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SnapshotMode = Literal[
  "paths",
  "globs",
  "all_admissible",
]


class RepoSnapshotPacketMetadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  document_id: Literal["repo_snapshot_packet.json"]
  title: Literal["Repo Snapshot Packet"]
  purpose: Literal[
    "Compiled repo file evidence selected for a model call."
  ]
  source_format: Literal["json"]
  document_authority: Literal["compiled_runtime_artifact"]


class RepoSnapshotSelection(BaseModel):
  model_config = ConfigDict(extra="forbid")

  mode: SnapshotMode
  include_harness: bool = False
  explicit_path_overrides_default_exclusions: bool = False
  repo_root: str
  requested_paths: list[str] = Field(default_factory=list)
  requested_globs: list[str] = Field(default_factory=list)
  exclusions: list[str] = Field(default_factory=list)
  gitignore_respected: bool
  harness_excluded: bool


class RepoSnapshotFile(BaseModel):
  model_config = ConfigDict(extra="forbid")

  path: str
  explicit_requested_path: bool = False
  size_bytes: int
  sha256: str
  encoding: Literal["utf-8"]
  content: str


class OmittedRepoSnapshotFile(BaseModel):
  model_config = ConfigDict(extra="forbid")

  path: str
  reason: Literal[
    "gitignored",
    "harness_excluded",
    "excluded_path",
    "binary",
    "too_large",
    "not_found",
    "outside_repo",
    "read_error",
  ]
  detail: str | None = None


class RepoSnapshotSummary(BaseModel):
  model_config = ConfigDict(extra="forbid")

  included_count: int
  omitted_count: int
  total_included_bytes: int


class RepoSnapshotPacket(BaseModel):
  model_config = ConfigDict(extra="forbid")

  metadata: RepoSnapshotPacketMetadata
  selection: RepoSnapshotSelection
  files: list[RepoSnapshotFile]
  omitted_files: list[OmittedRepoSnapshotFile] = Field(default_factory=list)
  summary: RepoSnapshotSummary
