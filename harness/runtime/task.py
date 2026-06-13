from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskMetadata(BaseModel):
  model_config = ConfigDict(extra="forbid")

  document_id: Literal["task.json"]
  title: Literal["Task"]
  purpose: Literal["Records the current user task for a harness run."]
  source_format: Literal["json"]
  document_authority: Literal["operational_state"]


class Task(BaseModel):
  model_config = ConfigDict(extra="forbid")

  metadata: TaskMetadata
  task_text: str = Field(min_length=1)
  source: Literal["cli"]


def task_from_cli(task_text: str) -> Task:
  return Task(
    metadata=TaskMetadata(
      document_id="task.json",
      title="Task",
      purpose="Records the current user task for a harness run.",
      source_format="json",
      document_authority="operational_state",
    ),
    task_text=task_text,
    source="cli",
  )
