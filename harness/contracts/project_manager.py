from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReportStatus = Literal["admissible", "admissibility-blocked"]
CheckStatus = Literal["pass", "fail", "blocked"]


class ReportSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReportStatus = Field(
        description="Whether this section is grounded or blocked by missing authority."
    )
    findings: list[str] = Field(
        min_length=1,
        description="Evidence-grounded findings for this report section.",
    )
    missing_basis: list[str] = Field(
        default_factory=list,
        description="Specific missing evidence or authority that blocks the section.",
    )


class AdmissibilityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Name of the check being evaluated.")
    status: CheckStatus = Field(description="Check result.")
    evidence: str = Field(description="Evidence, inference, or missing basis for the result.")
    missing_basis: str | None = Field(
        default=None,
        description="Required evidence or authority when the check is blocked.",
    )


class SourceCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(description="Context source identifier.")
    used: bool = Field(description="Whether the report used this source.")
    claims_supported: list[str] = Field(
        default_factory=list,
        description="Report claims or sections supported by the source when used.",
    )
    reason: str | None = Field(
        default=None,
        description="Why the source was unused when used is false.",
    )

    @model_validator(mode="after")
    def _validate_coverage(self) -> "SourceCoverage":
        if self.used:
            if not self.claims_supported:
                raise ValueError("Used source coverage entries must list claims_supported.")
            if self.reason is not None:
                raise ValueError("Used source coverage entries must not include a reason.")
        else:
            if self.claims_supported:
                raise ValueError("Unused source coverage entries must not include claims_supported.")
            if not self.reason:
                raise ValueError("Unused source coverage entries must include a reason.")
        return self


class ProjectManagerReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ReportStatus = Field(description="Overall PM admissibility status.")
    invariant_constraints: ReportSection
    task_constraints: ReportSection
    constraint_conflicts: ReportSection
    allowed_transformation_types: ReportSection
    affected_surfaces: ReportSection
    non_affected_surfaces: ReportSection
    admissibility_checks: list[AdmissibilityCheck] = Field(min_length=1)
    source_coverage: list[SourceCoverage] = Field(min_length=1)
    stop_conditions: ReportSection
    current_posture: str = Field(
        description="Concrete current repo posture derived from supplied context."
    )
    thesis_attractor: str = Field(
        description="Project direction derived from project spec authority."
    )
    structural_tension: str = Field(
        description="Dominant evidence, authority, constraint, or verification gap."
    )
    dominant_tension_justification: str = Field(
        description="Why the selected tension governs the current trajectory."
    )
    proof_frontier: str = Field(
        description="Next evidence-producing boundary that would reduce uncertainty."
    )
    next_admissible_transition: str = Field(
        description="One bounded transformation inside current authority."
    )
    summary: str = Field(description="Short terminal-safe summary of the report.")


class TaskBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_text: str
    created_at: datetime
    role_id: str
    role_name: str
    mode: str
    run_id: str
    context_sources: list[str]
