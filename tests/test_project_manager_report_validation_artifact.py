from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from harness.contracts.project_manager_report_extractor import (
  ProjectManagerReportExtractorError,
  extract_project_manager_report,
)
from harness.contracts.project_manager_report_validation import (
  PROJECT_MANAGER_REPORT_VALIDATOR,
  ProjectManagerReportValidationArtifact,
  default_validation_artifact_path,
)
from harness.runtime.artifact_facts import sha256_file


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"
RAW_RESPONSE_FIXTURE_PATH = FIXTURES_ROOT / "raw_model_response.json"
PM_SCHEMA_PATH = REPO_ROOT / "harness" / "contracts" / "ProjectManagerReport.schema.json"


def load_json(path: Path) -> dict:
  return json.loads(path.read_text(encoding="utf-8"))


class ProjectManagerReportValidationArtifactTests(unittest.TestCase):
  def test_validation_artifact_model_defaults_and_path_helper(self) -> None:
    artifact = ProjectManagerReportValidationArtifact(
      report_artifact_path="/tmp/project_manager_report.json",
      report_artifact_sha256="abc123",
      schema_name="project_manager_report",
      schema_path="/tmp/ProjectManagerReport.schema.json",
      schema_sha256="def456",
      validation_passed=True,
      report_status="needs_clarification",
      proof_frontier_blocked=True,
    )

    self.assertEqual(artifact.validator, PROJECT_MANAGER_REPORT_VALIDATOR)
    self.assertTrue(artifact.validation_passed)
    self.assertTrue(artifact.validation_timestamp_utc.endswith("Z"))
    datetime.fromisoformat(artifact.validation_timestamp_utc.replace("Z", "+00:00"))
    self.assertEqual(
      default_validation_artifact_path(Path("/tmp/project_manager_report.json")),
      Path("/tmp/project_manager_report.validation.json"),
    )

  def test_extractor_writes_validation_artifact_with_matching_hashes(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      output_path = temp_root / "project_manager_report.json"

      report = extract_project_manager_report(
        raw_response_path=RAW_RESPONSE_FIXTURE_PATH,
        schema_path=PM_SCHEMA_PATH,
        output_path=output_path,
      )

      validation_path = default_validation_artifact_path(output_path)
      self.assertTrue(output_path.is_file())
      self.assertTrue(validation_path.is_file())

      artifact = ProjectManagerReportValidationArtifact.model_validate(
        load_json(validation_path)
      )

      self.assertEqual(artifact.report_artifact_path, output_path.as_posix())
      self.assertEqual(artifact.report_artifact_sha256, sha256_file(output_path))
      self.assertEqual(artifact.schema_name, "project_manager_report")
      self.assertEqual(artifact.schema_path, PM_SCHEMA_PATH.as_posix())
      self.assertEqual(artifact.schema_sha256, sha256_file(PM_SCHEMA_PATH))
      self.assertTrue(artifact.validation_passed)
      self.assertEqual(artifact.report_status, report.report_status)
      self.assertEqual(artifact.proof_frontier_blocked, report.proof_frontier.blocked)
      self.assertEqual(report.report_status, "needs_clarification")

  def test_extractor_does_not_write_validation_artifact_on_failure(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      raw_response_path = temp_root / "raw_model_response.json"
      output_path = temp_root / "project_manager_report.json"
      validation_path = default_validation_artifact_path(output_path)
      raw_response = load_json(RAW_RESPONSE_FIXTURE_PATH)
      raw_response["status"] = "failed"
      raw_response_path.write_text(json.dumps(raw_response, indent=2) + "\n", encoding="utf-8")

      with self.assertRaises(ProjectManagerReportExtractorError):
        extract_project_manager_report(
          raw_response_path=raw_response_path,
          schema_path=PM_SCHEMA_PATH,
          output_path=output_path,
        )

      self.assertFalse(validation_path.exists())


if __name__ == "__main__":
  unittest.main()
