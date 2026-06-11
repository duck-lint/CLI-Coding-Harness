from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


ProviderId = Literal["openai"]
FallbackStrategy = Literal["fail", "first_allowed_fallback"]


class ProviderRuntimePolicyMetadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  document_id: Literal["provider_runtime.policy.json"]
  title: Literal["Provider Runtime Policy"]
  purpose: Literal[
    "Defines provider/model defaults, allowed models, and fallback behavior for provider rendering."
  ]
  source_format: Literal["json"]
  document_authority: Literal["runtime_policy"]


class ModelRef(BaseModel):
  model_config = ConfigDict(extra="forbid")

  provider: ProviderId
  model: str = Field(min_length=1)


class ProviderRuntimePolicy(BaseModel):
  model_config = ConfigDict(extra="forbid")

  schema_ref: str | None = Field(default=None, alias="$schema")
  metadata: ProviderRuntimePolicyMetadata
  default_direct_model: ModelRef
  allowed_models: dict[ProviderId, list[str]]
  fallback_strategy: FallbackStrategy = "fail"
  fallback_models: list[ModelRef] = Field(default_factory=list)
