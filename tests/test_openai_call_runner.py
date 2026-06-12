from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from harness.agents.agent_context_compiler import compile_agent_context_packet
from harness.providers.openai.openai_call_runner import (
  OpenAICallRunnerError,
  run_openai_call,
)
from harness.providers.openai.openai_raw_response import OpenAIRawResponse
from harness.providers.openai.openai_response_payload_compiler import (
  compile_openai_response_payload,
)
from harness.runtime.api_call_packet_builder import build_api_call_packet
from harness.runtime.task import task_from_cli


REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = REPO_ROOT / "harness"
MANIFEST_PATH = HARNESS_ROOT / "project_spec" / "static_context_packet.manifest.json"
AGENT_PATH = HARNESS_ROOT / "agents" / "project_manager.agent.json"
PM_SCHEMA_PATH = HARNESS_ROOT / "contracts" / "ProjectManagerReport.schema.json"
RAW_RESPONSE_SCHEMA_PATH = (
  HARNESS_ROOT / "providers" / "openai" / "OpenAIRawResponse.schema.json"
)


def load_json(path: Path) -> dict:
  return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def build_agent_routed_provider_payload(temp_root: Path) -> Path:
  agent_context_packet = compile_agent_context_packet(
    agent_path=AGENT_PATH,
    output_path=temp_root / "agent_context_packet.json",
    manifest_path=MANIFEST_PATH,
    harness_root=HARNESS_ROOT,
    target_repo_root=HARNESS_ROOT,
    static_context_output_path=temp_root / "static_context_packet.json",
  )
  build_api_call_packet(
    task=task_from_cli("Review the current project trajectory."),
    call_mode="agent_routed",
    agent_context_packet=agent_context_packet,
    output_path=temp_root / "api_call_packet.json",
  )
  provider_payload_path = temp_root / "provider_payload.json"
  compile_openai_response_payload(
    api_call_packet_path=temp_root / "api_call_packet.json",
    output_path=provider_payload_path,
  )
  return provider_payload_path


class FakeResponse:
  def __init__(
    self,
    *,
    raw_response: dict,
    response_id: str | None = "resp_123",
    model: str | None = "gpt-5.4",
    status: str | None = "completed",
    output_text: str | None = "{\"status\":\"admissible\"}",
  ) -> None:
    self.id = response_id
    self.model = model
    self.status = status
    self.output_text = output_text
    self._raw_response = raw_response

  def model_dump(self, mode: str = "json") -> dict:
    return dict(self._raw_response)


class FakeOpenAIClient:
  last_request_kwargs: dict | None = None
  next_response: FakeResponse | None = None
  error_to_raise: Exception | None = None

  class _Responses:
    def create(self, **kwargs):
      FakeOpenAIClient.last_request_kwargs = kwargs
      if FakeOpenAIClient.error_to_raise is not None:
        raise FakeOpenAIClient.error_to_raise
      if FakeOpenAIClient.next_response is None:
        raise AssertionError("No fake response configured.")
      return FakeOpenAIClient.next_response

  def __init__(self) -> None:
    self.responses = self._Responses()


class OpenAICallRunnerTests(unittest.TestCase):
  def setUp(self) -> None:
    FakeOpenAIClient.last_request_kwargs = None
    FakeOpenAIClient.error_to_raise = None
    FakeOpenAIClient.next_response = None

  def test_runner_loads_and_validates_openai_response_payload(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)
      FakeOpenAIClient.next_response = FakeResponse(
        raw_response={"id": "resp_123", "model": "gpt-5.4", "status": "completed"}
      )

      with patch(
        "harness.providers.openai.openai_call_runner._load_openai_client_class",
        return_value=FakeOpenAIClient,
      ):
        artifact = run_openai_call(
          provider_payload_path=provider_payload_path,
          output_path=temp_root / "raw_model_response.json",
        )

      self.assertIsInstance(artifact, OpenAIRawResponse)

  def test_runner_sends_only_payload_request_not_harness_metadata(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)
      payload = load_json(provider_payload_path)
      expected_request = {
        key: value
        for key, value in payload["request"].items()
        if value is not None
      }
      FakeOpenAIClient.next_response = FakeResponse(
        raw_response={"id": "resp_123", "model": "gpt-5.4", "status": "completed"}
      )

      with patch(
        "harness.providers.openai.openai_call_runner._load_openai_client_class",
        return_value=FakeOpenAIClient,
      ):
        run_openai_call(
          provider_payload_path=provider_payload_path,
          output_path=temp_root / "raw_model_response.json",
        )

      self.assertEqual(FakeOpenAIClient.last_request_kwargs, expected_request)
      self.assertNotIn("metadata", FakeOpenAIClient.last_request_kwargs)
      self.assertNotIn("provider", FakeOpenAIClient.last_request_kwargs)
      self.assertNotIn("endpoint", FakeOpenAIClient.last_request_kwargs)
      self.assertNotIn("source_artifacts", FakeOpenAIClient.last_request_kwargs)

  def test_runner_fails_if_payload_provider_is_not_openai(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)
      payload = load_json(provider_payload_path)
      payload["provider"] = "anthropic"
      write_json(provider_payload_path, payload)

      with self.assertRaises(OpenAICallRunnerError) as error:
        run_openai_call(
          provider_payload_path=provider_payload_path,
          output_path=temp_root / "raw_model_response.json",
        )

      self.assertIn("provider == 'openai'", str(error.exception))
      self.assertFalse((temp_root / "raw_model_response.json").exists())

  def test_runner_fails_if_payload_endpoint_is_not_responses_create(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)
      payload = load_json(provider_payload_path)
      payload["endpoint"] = "chat.completions.create"
      write_json(provider_payload_path, payload)

      with self.assertRaises(OpenAICallRunnerError) as error:
        run_openai_call(
          provider_payload_path=provider_payload_path,
          output_path=temp_root / "raw_model_response.json",
        )

      self.assertIn("endpoint == 'responses.create'", str(error.exception))
      self.assertFalse((temp_root / "raw_model_response.json").exists())

  def test_runner_writes_raw_model_response_on_mocked_success(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)
      output_path = temp_root / "raw_model_response.json"
      FakeOpenAIClient.next_response = FakeResponse(
        raw_response={"id": "resp_123", "model": "gpt-5.4", "status": "completed"}
      )

      with patch(
        "harness.providers.openai.openai_call_runner._load_openai_client_class",
        return_value=FakeOpenAIClient,
      ):
        artifact = run_openai_call(
          provider_payload_path=provider_payload_path,
          output_path=output_path,
        )

      self.assertTrue(output_path.is_file())
      self.assertEqual(artifact.source_artifacts, ["provider_payload.json"])

  def test_runner_records_raw_response_body(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)
      raw_response = {
        "id": "resp_123",
        "model": "gpt-5.4",
        "status": "completed",
        "output": [{"type": "message"}],
      }
      FakeOpenAIClient.next_response = FakeResponse(raw_response=raw_response)

      with patch(
        "harness.providers.openai.openai_call_runner._load_openai_client_class",
        return_value=FakeOpenAIClient,
      ):
        artifact = run_openai_call(
          provider_payload_path=provider_payload_path,
          output_path=temp_root / "raw_model_response.json",
        )

      self.assertEqual(artifact.raw_response, raw_response)

  def test_runner_copies_response_fields_when_available(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)
      FakeOpenAIClient.next_response = FakeResponse(
        raw_response={
          "id": "resp_123",
          "model": "gpt-5.4",
          "status": "completed",
          "output_text": "{\"status\":\"admissible\"}",
        }
      )

      with patch(
        "harness.providers.openai.openai_call_runner._load_openai_client_class",
        return_value=FakeOpenAIClient,
      ):
        artifact = run_openai_call(
          provider_payload_path=provider_payload_path,
          output_path=temp_root / "raw_model_response.json",
        )

      self.assertEqual(artifact.response_id, "resp_123")
      self.assertEqual(artifact.model, "gpt-5.4")
      self.assertEqual(artifact.status, "completed")
      self.assertEqual(artifact.output_text, "{\"status\":\"admissible\"}")

  def test_runner_does_not_create_project_manager_report_json(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)
      FakeOpenAIClient.next_response = FakeResponse(
        raw_response={"id": "resp_123", "model": "gpt-5.4", "status": "completed"}
      )

      with patch(
        "harness.providers.openai.openai_call_runner._load_openai_client_class",
        return_value=FakeOpenAIClient,
      ):
        run_openai_call(
          provider_payload_path=provider_payload_path,
          output_path=temp_root / "raw_model_response.json",
        )

      self.assertFalse((temp_root / "project_manager_report.json").exists())

  def test_runner_does_not_perform_pm_report_schema_validation(self) -> None:
    module_source = inspect.getsource(
      sys.modules["harness.providers.openai.openai_call_runner"]
    )

    self.assertNotIn("ProjectManagerReport.schema.json", module_source)
    self.assertNotIn("project_manager_report.py", module_source)
    self.assertNotIn("jsonschema", module_source)

  def test_runner_does_not_make_real_network_calls_in_tests(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)
      FakeOpenAIClient.error_to_raise = AssertionError("mocked client path only")

      with patch(
        "harness.providers.openai.openai_call_runner._load_openai_client_class",
        return_value=FakeOpenAIClient,
      ):
        with self.assertRaises(OpenAICallRunnerError) as error:
          run_openai_call(
            provider_payload_path=provider_payload_path,
            output_path=temp_root / "raw_model_response.json",
          )

      self.assertIn("mocked client path only", str(error.exception))

  def test_runner_fails_clearly_if_openai_sdk_is_not_installed(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)

      with patch(
        "harness.providers.openai.openai_call_runner._load_openai_client_class",
        side_effect=OpenAICallRunnerError("OpenAI SDK is not installed."),
      ):
        with self.assertRaises(OpenAICallRunnerError) as error:
          run_openai_call(
            provider_payload_path=provider_payload_path,
            output_path=temp_root / "raw_model_response.json",
          )

      self.assertEqual(str(error.exception), "OpenAI SDK is not installed.")
      self.assertFalse((temp_root / "raw_model_response.json").exists())

  def test_runner_direct_script_supports_provider_payload_and_output(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)
      output_path = temp_root / "raw_model_response.json"
      fake_openai_root = temp_root / "fake_openai"
      fake_openai_root.mkdir()
      (fake_openai_root / "openai.py").write_text(
        textwrap.dedent(
          """
          class _Response:
            id = "resp_script"
            model = "gpt-5.4"
            status = "completed"
            output_text = "{\\"ok\\":true}"

            def model_dump(self, mode="json"):
              return {
                "id": self.id,
                "model": self.model,
                "status": self.status,
                "output_text": self.output_text,
              }

          class _Responses:
            def create(self, **kwargs):
              return _Response()

          class OpenAI:
            def __init__(self):
              self.responses = _Responses()
          """
        ),
        encoding="utf-8",
      )
      script_path = HARNESS_ROOT / "providers" / "openai" / "openai_call_runner.py"
      env = dict(os.environ)
      env["PYTHONDONTWRITEBYTECODE"] = "1"
      env["PYTHONPATH"] = str(fake_openai_root)

      completed = subprocess.run(
        [
          sys.executable,
          str(script_path),
          "--provider-payload",
          str(provider_payload_path),
          "--output",
          str(output_path),
        ],
        cwd=script_path.parent,
        capture_output=True,
        text=True,
        check=False,
        env=env,
      )

      self.assertEqual(completed.returncode, 0, completed.stderr)
      self.assertTrue(output_path.is_file())
      self.assertIn("PASS: OpenAI raw response written", completed.stdout)
      self.assertIn("Response id: resp_script", completed.stdout)

  def test_package_cli_still_fails_honestly(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      runs_root = Path(temp_directory) / "runs"
      completed = subprocess.run(
        [
          sys.executable,
          "-m",
          "harness",
          "Review the current project trajectory.",
          "--runs-root",
          str(runs_root),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
      )

      self.assertEqual(completed.returncode, 1)
      self.assertIn("package CLI is not implemented yet", completed.stderr)
      self.assertFalse(runs_root.exists())

  def test_emitted_raw_response_validates_against_generated_schema(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      provider_payload_path = build_agent_routed_provider_payload(temp_root)
      FakeOpenAIClient.next_response = FakeResponse(
        raw_response={"id": "resp_123", "model": "gpt-5.4", "status": "completed"}
      )

      with patch(
        "harness.providers.openai.openai_call_runner._load_openai_client_class",
        return_value=FakeOpenAIClient,
      ):
        artifact = run_openai_call(
          provider_payload_path=provider_payload_path,
          output_path=temp_root / "raw_model_response.json",
        )

      schema = load_json(RAW_RESPONSE_SCHEMA_PATH)
      Draft202012Validator.check_schema(schema)
      Draft202012Validator(schema).validate(
        load_json(temp_root / "raw_model_response.json")
      )
      self.assertIsInstance(artifact, OpenAIRawResponse)


if __name__ == "__main__":
  unittest.main()
