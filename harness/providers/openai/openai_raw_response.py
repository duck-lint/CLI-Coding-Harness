from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OpenAIRawResponseMetadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  document_id: Literal["raw_model_response.json"]
  title: Literal["OpenAI Raw Model Response"]
  purpose: Literal[
    "Raw OpenAI Responses API result captured before harness output validation."
  ]
  source_format: Literal["json"]
  document_authority: Literal["raw_provider_artifact"]


class OpenAIRawResponse(BaseModel):
  model_config = ConfigDict(extra="forbid")

  metadata: OpenAIRawResponseMetadata
  provider: Literal["openai"]
  endpoint: Literal["responses.create"]
  response_id: str | None = None
  model: str | None = None
  status: str | None = None
  output_text: str | None = None
  raw_response: dict[str, Any]
  source_artifacts: list[str] = Field(default_factory=list)
  basis: list[str] = Field(default_factory=list)
