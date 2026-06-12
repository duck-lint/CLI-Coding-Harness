from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# Support direct execution from harness/providers/openai while preserving package imports.
if __package__ in {None, ""}:
  sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pydantic import ValidationError

from harness.providers.openai.openai_raw_response import (
  OpenAIRawResponse,
  OpenAIRawResponseMetadata,
)
from harness.providers.openai.openai_response_payload import OpenAIResponsePayload


class OpenAICallRunnerError(RuntimeError):
  pass


def _load_json(path: Path) -> dict[str, Any]:
  with path.open("r", encoding="utf-8") as file:
    data = json.load(file)

  if not isinstance(data, dict):
    raise TypeError(f"Expected a JSON object in {path}.")

  return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", encoding="utf-8") as file:
    json.dump(data, file, indent=2)
    file.write("\n")


def _load_openai_client_class():
  try:
    from openai import OpenAI
  except ImportError as error:
    raise OpenAICallRunnerError("OpenAI SDK is not installed.") from error

  return OpenAI


def _response_to_json_dict(response: Any) -> dict[str, Any]:
  if hasattr(response, "model_dump"):
    data = response.model_dump(mode="json")
  elif hasattr(response, "to_dict"):
    data = response.to_dict()
  elif isinstance(response, dict):
    data = response
  else:
    raise OpenAICallRunnerError(
      "OpenAI response object could not be converted to JSON."
    )

  if not isinstance(data, dict):
    raise OpenAICallRunnerError("OpenAI response JSON payload must be an object.")

  return data


def _extract_output_text(response: Any, raw_response: dict[str, Any]) -> str | None:
  output_text = getattr(response, "output_text", None)
  if isinstance(output_text, str):
    return output_text

  raw_output_text = raw_response.get("output_text")
  if isinstance(raw_output_text, str):
    return raw_output_text

  return None


def run_openai_call(
  *,
  provider_payload_path: Path,
  output_path: Path,
) -> OpenAIRawResponse:
  raw_payload = _load_json(provider_payload_path)

  if raw_payload.get("provider") != "openai":
    raise OpenAICallRunnerError(
      "OpenAI call runner requires provider payload provider == 'openai'."
    )

  if raw_payload.get("endpoint") != "responses.create":
    raise OpenAICallRunnerError(
      "OpenAI call runner requires provider payload endpoint == 'responses.create'."
    )

  payload = OpenAIResponsePayload.model_validate(raw_payload)

  request_body = payload.request.model_dump(
    mode="json",
    by_alias=True,
    exclude_none=True,
  )

  OpenAI = _load_openai_client_class()

  repo_root = Path(__file__).resolve().parents[3]
  load_dotenv(repo_root / ".env.local")

  try:
    client = OpenAI()
    response = client.responses.create(**request_body)
  except Exception as error:
    raise OpenAICallRunnerError(str(error)) from error

  raw_response = _response_to_json_dict(response)
  response_id = getattr(response, "id", None)
  if not isinstance(response_id, str):
    response_id = raw_response.get("id")
  model = getattr(response, "model", None)
  if not isinstance(model, str):
    model = raw_response.get("model")
  status = getattr(response, "status", None)
  if not isinstance(status, str):
    status = raw_response.get("status")

  artifact = OpenAIRawResponse(
    metadata=OpenAIRawResponseMetadata(
      document_id="raw_model_response.json",
      title="OpenAI Raw Model Response",
      purpose=(
        "Raw OpenAI Responses API result captured before harness output validation."
      ),
      source_format="json",
      document_authority="generated_artifact",
    ),
    provider="openai",
    endpoint="responses.create",
    response_id=response_id if isinstance(response_id, str) else None,
    model=model if isinstance(model, str) else None,
    status=status if isinstance(status, str) else None,
    output_text=_extract_output_text(response, raw_response),
    raw_response=raw_response,
    source_artifacts=[provider_payload_path.name],
    basis=[
      "Called OpenAI Responses API using rendered provider payload.",
      "Captured raw provider response before harness output validation.",
      "No ProjectManagerReport validation was performed.",
    ],
  )

  _write_json(output_path, artifact.model_dump(mode="json", by_alias=True))
  return OpenAIRawResponse.model_validate(_load_json(output_path))


def build_argument_parser() -> argparse.ArgumentParser:
  script_path = Path(__file__).resolve()
  harness_root = script_path.parents[2]

  parser = argparse.ArgumentParser(
    description="Send a rendered OpenAI provider payload and capture the raw model response.",
  )
  parser.add_argument(
    "--provider-payload",
    type=Path,
    required=True,
    help="Path to OpenAI provider payload JSON artifact.",
  )
  parser.add_argument(
    "--output",
    type=Path,
    default=harness_root / "runs" / "raw_model_response.json",
    help="Destination for the emitted raw OpenAI response JSON.",
  )
  return parser


def main(argv: list[str] | None = None) -> int:
  args = build_argument_parser().parse_args(argv)

  try:
    artifact = run_openai_call(
      provider_payload_path=args.provider_payload.resolve(),
      output_path=args.output.resolve(),
    )
  except (
    OpenAICallRunnerError,
    OSError,
    TypeError,
    ValidationError,
    ValueError,
  ) as error:
    print(f"FAIL: {error}", file=sys.stderr)
    return 1

  print(f"PASS: OpenAI raw response written to {args.output.resolve()}")
  print(f"Response id: {artifact.response_id}")
  print(f"Status: {artifact.status}")
  print(f"Model: {artifact.model}")
  print(f"Output text present: {'yes' if artifact.output_text else 'no'}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
