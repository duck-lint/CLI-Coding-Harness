from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


DEFAULT_RUNTIME_CALL_LEDGER_PATH = (
  Path(__file__).resolve().parents[1] / "runs" / "ledgers" / "api_call_ledger.jsonl"
)


def utc_now_isoformat() -> str:
  return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def generate_local_call_id() -> str:
  return uuid.uuid4().hex


def ensure_parent_directory(path: Path) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)


class RuntimeCallRecord(BaseModel):
  model_config = ConfigDict(extra="forbid")

  ledger_version: Literal["0.1"] = "0.1"
  timestamp_utc: str = Field(default_factory=utc_now_isoformat)
  local_call_id: str = Field(default_factory=generate_local_call_id)
  route: str
  agent: str
  model: str
  schema_name: str
  context_packet_sha256: str
  validation_passed: bool
  estimated_input_tokens: int | None = None
  actual_input_tokens: int | None = None
  actual_output_tokens: int | None = None
  total_tokens: int | None = None
  openai_response_id: str | None = None
  contract_status: str | None = None
  output_artifact_path: str | None = None
  git_commit: str | None = None
  worktree_dirty: bool | None = None
  notes: str | None = None


def append_runtime_call_record(
  record: RuntimeCallRecord,
  *,
  path: Path = DEFAULT_RUNTIME_CALL_LEDGER_PATH,
) -> Path:
  ensure_parent_directory(path)
  with path.open("a", encoding="utf-8") as file:
    file.write(record.model_dump_json(exclude_none=True))
    file.write("\n")
  return path


def _provider_response_raw_mapping(provider_response: Any) -> dict[str, Any] | None:
  raw_response = getattr(provider_response, "raw_response", None)
  if isinstance(raw_response, dict):
    return raw_response

  if isinstance(provider_response, dict):
    nested_raw_response = provider_response.get("raw_response")
    if isinstance(nested_raw_response, dict):
      return nested_raw_response
    return provider_response

  if hasattr(provider_response, "model_dump"):
    data = provider_response.model_dump(mode="json")
    if isinstance(data, dict):
      nested_raw_response = data.get("raw_response")
      if isinstance(nested_raw_response, dict):
        return nested_raw_response
      return data

  return None


def _provider_response_string(provider_response: Any, *keys: str) -> str | None:
  for key in keys:
    value = getattr(provider_response, key, None)
    if isinstance(value, str):
      return value

  if isinstance(provider_response, dict):
    for key in keys:
      value = provider_response.get(key)
      if isinstance(value, str):
        return value

  raw_response = _provider_response_raw_mapping(provider_response)
  if isinstance(raw_response, dict):
    for key in keys:
      value = raw_response.get(key)
      if isinstance(value, str):
        return value

  return None


def _provider_response_usage_value(provider_response: Any, key: str) -> int | None:
  raw_response = _provider_response_raw_mapping(provider_response)
  if not isinstance(raw_response, dict):
    return None

  usage = raw_response.get("usage")
  if not isinstance(usage, dict):
    return None

  value = usage.get(key)
  return value if isinstance(value, int) else None


def finalize_runtime_call_ledger(
  *,
  route: str,
  agent: str,
  model: str,
  schema_name: str,
  context_packet_sha256: str,
  validation_passed: bool,
  provider_response: Any | None = None,
  estimated_input_tokens: int | None = None,
  actual_input_tokens: int | None = None,
  actual_output_tokens: int | None = None,
  total_tokens: int | None = None,
  openai_response_id: str | None = None,
  contract_status: str | None = None,
  output_artifact_path: str | None = None,
  git_commit: str | None = None,
  worktree_dirty: bool | None = None,
  notes: str | None = None,
  path: Path = DEFAULT_RUNTIME_CALL_LEDGER_PATH,
) -> RuntimeCallRecord:
  if provider_response is not None:
    if openai_response_id is None:
      openai_response_id = _provider_response_string(
        provider_response,
        "response_id",
        "id",
      )

    if actual_input_tokens is None:
      actual_input_tokens = _provider_response_usage_value(
        provider_response,
        "input_tokens",
      )

    if actual_output_tokens is None:
      actual_output_tokens = _provider_response_usage_value(
        provider_response,
        "output_tokens",
      )

    if total_tokens is None:
      total_tokens = _provider_response_usage_value(
        provider_response,
        "total_tokens",
      )

  try:
    record = RuntimeCallRecord(
      route=route,
      agent=agent,
      model=model,
      schema_name=schema_name,
      context_packet_sha256=context_packet_sha256,
      validation_passed=validation_passed,
      estimated_input_tokens=estimated_input_tokens,
      actual_input_tokens=actual_input_tokens,
      actual_output_tokens=actual_output_tokens,
      total_tokens=total_tokens,
      openai_response_id=openai_response_id,
      contract_status=contract_status,
      output_artifact_path=output_artifact_path,
      git_commit=git_commit,
      worktree_dirty=worktree_dirty,
      notes=notes,
    )
    append_runtime_call_record(record, path=path)
  except (OSError, TypeError, ValueError, ValidationError) as error:
    raise RuntimeError(
      f"Call succeeded but ledger persistence failed: {error}"
    ) from error

  return record
