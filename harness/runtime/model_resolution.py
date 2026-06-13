from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Literal

# Support direct execution from harness/runtime while preserving package imports.
if __package__ in {None, ""}:
  sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from harness.runtime.api_call_packet import ApiCallPacket
from harness.runtime.provider_runtime_policy import ModelRef, ProviderRuntimePolicy


ModelSelectionSource = Literal[
  "agent_contract",
  "provider_runtime_policy.default_direct_model",
  "provider_runtime_policy.fallback_model",
]


class EffectiveModelSelectionMetadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  document_id: Literal["effective_model_selection.json"]
  title: Literal["Effective Model Selection"]
  purpose: Literal[
    "Records deterministic provider/model selection before provider-specific payload rendering."
  ]
  source_format: Literal["json"]
  document_authority: Literal["compiled_runtime_artifact"]


class EffectiveModelSelection(BaseModel):
  model_config = ConfigDict(extra="forbid")

  metadata: EffectiveModelSelectionMetadata
  provider: str
  model: str
  source: ModelSelectionSource
  fallback_used: bool = False
  requested_model: str | None = None
  basis: list[str] = Field(default_factory=list)


class ModelResolutionError(ValueError):
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


def is_allowed_model(model_ref: ModelRef, policy: ProviderRuntimePolicy) -> bool:
  return model_ref.model in policy.allowed_models.get(model_ref.provider, [])


def _first_allowed_fallback(
  policy: ProviderRuntimePolicy,
) -> ModelRef | None:
  for model_ref in policy.fallback_models:
    if is_allowed_model(model_ref, policy):
      return model_ref
  return None


def _fallback_or_raise(
  *,
  requested_model: str,
  provider_runtime_policy: ProviderRuntimePolicy,
  failure_basis: str,
) -> EffectiveModelSelection:
  if provider_runtime_policy.fallback_strategy == "fail":
    raise ModelResolutionError(failure_basis)

  fallback_model = _first_allowed_fallback(provider_runtime_policy)
  if fallback_model is None:
    raise ModelResolutionError(
      f"{failure_basis} No allowed fallback model is configured."
    )

  return EffectiveModelSelection(
    metadata=EffectiveModelSelectionMetadata(
      document_id="effective_model_selection.json",
      title="Effective Model Selection",
      purpose=(
        "Records deterministic provider/model selection before "
        "provider-specific payload rendering."
      ),
      source_format="json",
      document_authority="compiled_runtime_artifact",
    ),
    provider=fallback_model.provider,
    model=fallback_model.model,
    source="provider_runtime_policy.fallback_model",
    fallback_used=True,
    requested_model=requested_model,
    basis=[
      failure_basis,
      "Provider runtime policy selected the first allowed fallback model.",
    ],
  )


def resolve_effective_model(
  *,
  api_call_packet: ApiCallPacket,
  provider_runtime_policy: ProviderRuntimePolicy,
) -> EffectiveModelSelection:
  if api_call_packet.call_mode == "agent_routed":
    if api_call_packet.agent_context_packet is None:
      raise ModelResolutionError(
        "agent_routed ApiCallPacket requires agent_context_packet."
      )

    requested_model = api_call_packet.agent_context_packet.agent_contract.model
    if not requested_model:
      raise ModelResolutionError(
        "Agent contract model is missing for agent-routed call."
      )

    requested_model_ref = ModelRef(
      provider=provider_runtime_policy.default_direct_model.provider,
      model=requested_model,
    )
    if is_allowed_model(requested_model_ref, provider_runtime_policy):
      return EffectiveModelSelection(
        metadata=EffectiveModelSelectionMetadata(
          document_id="effective_model_selection.json",
          title="Effective Model Selection",
          purpose=(
            "Records deterministic provider/model selection before "
            "provider-specific payload rendering."
          ),
          source_format="json",
          document_authority="compiled_runtime_artifact",
        ),
        provider=requested_model_ref.provider,
        model=requested_model_ref.model,
        source="agent_contract",
        fallback_used=False,
        requested_model=requested_model_ref.model,
        basis=[
          "Agent-routed call uses the selected agent contract model as primary authority.",
          f"Requested model {requested_model_ref.model} is allowed by provider runtime policy.",
        ],
      )

    return _fallback_or_raise(
      requested_model=requested_model_ref.model,
      provider_runtime_policy=provider_runtime_policy,
      failure_basis=(
        "Agent contract model is disallowed by provider runtime policy."
      ),
    )

  direct_model_ref = provider_runtime_policy.default_direct_model
  if is_allowed_model(direct_model_ref, provider_runtime_policy):
    return EffectiveModelSelection(
      metadata=EffectiveModelSelectionMetadata(
        document_id="effective_model_selection.json",
        title="Effective Model Selection",
        purpose=(
          "Records deterministic provider/model selection before "
          "provider-specific payload rendering."
        ),
        source_format="json",
        document_authority="compiled_runtime_artifact",
      ),
      provider=direct_model_ref.provider,
      model=direct_model_ref.model,
      source="provider_runtime_policy.default_direct_model",
      fallback_used=False,
      basis=[
        "Direct call uses provider runtime policy default model.",
        f"Default direct model {direct_model_ref.model} is allowed by policy.",
      ],
    )

  return _fallback_or_raise(
    requested_model=direct_model_ref.model,
    provider_runtime_policy=provider_runtime_policy,
    failure_basis=(
      "Provider runtime policy default direct model is disallowed by policy."
    ),
  )


def write_effective_model_selection(
  *,
  api_call_packet_path: Path,
  provider_runtime_policy_path: Path,
  output_path: Path,
) -> EffectiveModelSelection:
  api_call_packet = ApiCallPacket.model_validate(_load_json(api_call_packet_path))
  provider_runtime_policy = ProviderRuntimePolicy.model_validate(
    _load_json(provider_runtime_policy_path)
  )
  selection = resolve_effective_model(
    api_call_packet=api_call_packet,
    provider_runtime_policy=provider_runtime_policy,
  )
  _write_json(output_path, selection.model_dump(mode="json"))
  return EffectiveModelSelection.model_validate(_load_json(output_path))


def build_argument_parser() -> argparse.ArgumentParser:
  script_path = Path(__file__).resolve()
  harness_root = script_path.parents[1]

  parser = argparse.ArgumentParser(
    description="Resolve effective provider/model selection for an ApiCallPacket.",
  )
  parser.add_argument(
    "--api-call-packet",
    type=Path,
    required=True,
    help="Path to an ApiCallPacket JSON artifact.",
  )
  parser.add_argument(
    "--provider-runtime-policy",
    type=Path,
    default=harness_root / "runtime" / "provider_runtime.policy.json",
    help="Path to ProviderRuntimePolicy JSON.",
  )
  parser.add_argument(
    "--output",
    type=Path,
    default=None,
    help="Destination for effective_model_selection.json. Defaults beside the API call packet.",
  )
  return parser


def main(argv: list[str] | None = None) -> int:
  args = build_argument_parser().parse_args(argv)
  output_path = (
    args.output.resolve()
    if args.output is not None
    else args.api_call_packet.resolve().with_name("effective_model_selection.json")
  )

  try:
    selection = write_effective_model_selection(
      api_call_packet_path=args.api_call_packet.resolve(),
      provider_runtime_policy_path=args.provider_runtime_policy.resolve(),
      output_path=output_path,
    )
  except (
    ModelResolutionError,
    OSError,
    TypeError,
    ValidationError,
    ValueError,
  ) as error:
    print(f"FAIL: {error}", file=sys.stderr)
    return 1

  print(f"PASS: Effective model selection written to {output_path}")
  print(f"Provider: {selection.provider}")
  print(f"Model: {selection.model}")
  print(f"Source: {selection.source}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
