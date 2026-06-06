from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class KnownFailureEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    pattern: str
    trigger: str
    symptom: str
    likely_cause: str
    prevention_rule: str
    cheapest_check: str
    last_seen: str
    status: str
