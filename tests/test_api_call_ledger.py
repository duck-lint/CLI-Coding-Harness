from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from harness.runtime.api_call_ledger import (
  DEFAULT_RUNTIME_CALL_LEDGER_PATH,
  RuntimeCallRecord,
  append_runtime_call_record,
  finalize_runtime_call_ledger,
  utc_now_isoformat,
)


class RuntimeCallLedgerTests(unittest.TestCase):
  def test_runtime_call_record_defaults_and_optional_fields(self) -> None:
    record = RuntimeCallRecord(
      route="plan",
      agent="harness/agents/project_manager.agent.json",
      model="gpt-5.4-mini",
      schema_name="project_manager_report",
      context_packet_sha256="abc123",
      validation_passed=True,
    )

    self.assertEqual(record.ledger_version, "0.1")
    self.assertTrue(record.timestamp_utc.endswith("Z"))
    datetime.fromisoformat(record.timestamp_utc.replace("Z", "+00:00"))
    self.assertIsInstance(record.local_call_id, str)
    self.assertEqual(record.route, "plan")
    self.assertEqual(record.model, "gpt-5.4-mini")
    self.assertIsNone(record.estimated_input_tokens)
    self.assertIsNone(record.actual_input_tokens)
    self.assertIsNone(record.actual_output_tokens)
    self.assertIsNone(record.total_tokens)
    self.assertIsNone(record.openai_response_id)
    self.assertIsNone(record.contract_status)
    self.assertIsNone(record.output_artifact_path)
    self.assertIsNone(record.report_artifact_path)
    self.assertIsNone(record.report_artifact_sha256)
    self.assertIsNone(record.validation_artifact_path)
    self.assertIsNone(record.validation_artifact_sha256)
    self.assertIsNone(record.git_commit)
    self.assertIsNone(record.worktree_dirty)
    self.assertIsNone(record.notes)

    dumped = record.model_dump(exclude_none=True)
    self.assertNotIn("estimated_input_tokens", dumped)
    self.assertNotIn("notes", dumped)

  def test_utc_now_isoformat_returns_utc_timestamp(self) -> None:
    timestamp = utc_now_isoformat()
    self.assertTrue(timestamp.endswith("Z"))
    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

  def test_append_runtime_call_record_creates_jsonl_file(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      ledger_path = Path(temp_directory) / "nested" / "api_call_ledger.jsonl"
      record = RuntimeCallRecord(
        route="plan",
        agent="harness/agents/project_manager.agent.json",
        model="gpt-5.4-mini",
        schema_name="project_manager_report",
        context_packet_sha256="abc123",
        validation_passed=True,
        openai_response_id="resp_123",
      )

      append_runtime_call_record(record, path=ledger_path)

      self.assertTrue(ledger_path.exists())
      lines = ledger_path.read_text(encoding="utf-8").splitlines()
      self.assertEqual(len(lines), 1)
      payload = json.loads(lines[0])
      self.assertEqual(payload["ledger_version"], "0.1")
      self.assertEqual(payload["route"], "plan")
      self.assertEqual(payload["openai_response_id"], "resp_123")
      self.assertTrue(payload["validation_passed"])
      RuntimeCallRecord.model_validate(payload)

  def test_append_runtime_call_record_appends_without_overwriting(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      ledger_path = Path(temp_directory) / "api_call_ledger.jsonl"

      append_runtime_call_record(
        RuntimeCallRecord(
          route="plan",
          agent="harness/agents/project_manager.agent.json",
          model="gpt-5.4-mini",
          schema_name="project_manager_report",
          context_packet_sha256="abc123",
          validation_passed=True,
        ),
        path=ledger_path,
      )
      append_runtime_call_record(
        RuntimeCallRecord(
          route="agent",
          agent="harness/agents/project_manager.agent.json",
          model="gpt-5.4",
          schema_name="project_manager_report",
          context_packet_sha256="def456",
          validation_passed=True,
          contract_status="needs_clarification",
        ),
        path=ledger_path,
      )

      lines = ledger_path.read_text(encoding="utf-8").splitlines()
      self.assertEqual(len(lines), 2)
      first_record = json.loads(lines[0])
      second_record = json.loads(lines[1])
      self.assertEqual(first_record["route"], "plan")
      self.assertEqual(second_record["route"], "agent")
      self.assertNotEqual(first_record["local_call_id"], second_record["local_call_id"])
      RuntimeCallRecord.model_validate(first_record)
      RuntimeCallRecord.model_validate(second_record)

  def test_finalize_runtime_call_ledger_captures_provider_response_usage(self) -> None:
    class FakeProviderResponse:
      def __init__(self) -> None:
        self.response_id = "resp_123"
        self.raw_response = {
          "id": "resp_123",
          "usage": {
            "input_tokens": 11,
            "output_tokens": 7,
            "total_tokens": 18,
          },
        }

    with tempfile.TemporaryDirectory() as temp_directory:
      ledger_path = Path(temp_directory) / "api_call_ledger.jsonl"

      record = finalize_runtime_call_ledger(
        route="plan",
        agent="harness/agents/project_manager.agent.json",
        model="gpt-5.4-mini",
        schema_name="project_manager_report",
        context_packet_sha256="abc123",
        validation_passed=True,
        provider_response=FakeProviderResponse(),
        contract_status="needs_clarification",
        output_artifact_path="harness/runs/example/project_manager_report.json",
        report_artifact_path="harness/runs/example/project_manager_report.json",
        report_artifact_sha256="abc123",
        validation_artifact_path=(
          "harness/runs/example/project_manager_report.validation.json"
        ),
        validation_artifact_sha256="def456",
        git_commit="deadbeef",
        worktree_dirty=False,
        path=ledger_path,
      )

      self.assertIsInstance(record, RuntimeCallRecord)
      lines = ledger_path.read_text(encoding="utf-8").splitlines()
      self.assertEqual(len(lines), 1)
      payload = json.loads(lines[0])
      self.assertEqual(payload["openai_response_id"], "resp_123")
      self.assertEqual(payload["actual_input_tokens"], 11)
      self.assertEqual(payload["actual_output_tokens"], 7)
      self.assertEqual(payload["total_tokens"], 18)
      self.assertEqual(payload["contract_status"], "needs_clarification")
      self.assertEqual(
        payload["output_artifact_path"],
        "harness/runs/example/project_manager_report.json",
      )
      self.assertEqual(
        payload["report_artifact_path"],
        "harness/runs/example/project_manager_report.json",
      )
      self.assertEqual(payload["report_artifact_sha256"], "abc123")
      self.assertEqual(
        payload["validation_artifact_path"],
        "harness/runs/example/project_manager_report.validation.json",
      )
      self.assertEqual(payload["validation_artifact_sha256"], "def456")
      RuntimeCallRecord.model_validate(payload)

  def test_default_ledger_path_points_to_state_ledgers(self) -> None:
    self.assertEqual(
      DEFAULT_RUNTIME_CALL_LEDGER_PATH.parts[-4:],
      ("harness", "state", "ledgers", "api_call_ledger.jsonl"),
    )


if __name__ == "__main__":
  unittest.main()
