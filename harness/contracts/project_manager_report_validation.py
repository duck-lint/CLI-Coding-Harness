from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from harness.runtime.artifact_facts import utc_now_isoformat


PROJECT_MANAGER_REPORT_VALIDATOR = (
  "harness.contracts.project_manager_report_extractor.extract_project_manager_report"
)


def default_validation_artifact_path(report_artifact_path: Path) -> Path:
  return report_artifact_path.with_name(f"{report_artifact_path.stem}.validation.json")


class ProjectManagerReportValidationArtifact(BaseModel):
  model_config = ConfigDict(extra="forbid")

  report_artifact_path: str
  report_artifact_sha256: str
  schema_name: str
  schema_path: str
  schema_sha256: str
  validator: str = PROJECT_MANAGER_REPORT_VALIDATOR
  validation_timestamp_utc: str = Field(default_factory=utc_now_isoformat)
  validation_passed: bool
  report_status: Literal[
    "admissible",
    "admissibility_blocked",
    "rejected",
    "needs_clarification",
  ]
  proof_frontier_blocked: bool
