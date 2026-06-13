from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OpenAIResponsePayloadMetadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  document_id: Literal["provider_payload.json"]
  title: Literal["OpenAI Response Payload"]
  purpose: Literal[
    "Provider-specific OpenAI Responses API payload rendered from a provider-neutral ApiCallPacket."
  ]
  source_format: Literal["json"]
  document_authority: Literal["compiled_runtime_artifact"]


class PayloadInputText(BaseModel):
  model_config = ConfigDict(extra="forbid")

  type: Literal["input_text"]
  text: str


class PayloadMessage(BaseModel):
  model_config = ConfigDict(extra="forbid")

  type: Literal["message"] = "message"
  role: Literal["developer", "user"]
  content: list[PayloadInputText]


class PayloadTextFormatSchema(BaseModel):
  model_config = ConfigDict(extra="forbid", populate_by_name=True)

  type: Literal["json_schema"]
  name: str
  strict: Literal[True]
  schema_: dict[str, Any] = Field(alias="schema")


class PayloadTextFormat(BaseModel):
  model_config = ConfigDict(extra="forbid")

  format: PayloadTextFormatSchema


class OpenAIResponseRequest(BaseModel):
  model_config = ConfigDict(extra="forbid")

  model: str
  input: list[PayloadMessage]
  text: PayloadTextFormat
  max_output_tokens: int | None = None
  tools: list[Any] = Field(default_factory=list)


class OpenAIResponsePayload(BaseModel):
  model_config = ConfigDict(extra="forbid")

  metadata: OpenAIResponsePayloadMetadata
  provider: Literal["openai"]
  endpoint: Literal["responses.create"]
  request: OpenAIResponseRequest
  source_artifacts: list[str] = Field(default_factory=list)
  basis: list[str] = Field(default_factory=list)
