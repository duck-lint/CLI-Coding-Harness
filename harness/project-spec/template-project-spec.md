# Project Spec

This file, together with the other docs under `harness/project-spec/`, is the authoritative invariant space for harnessed work in this repo.

Describe the project here, not the harness. Let the harness derive planning and execution guidance from this spec instead of embedding project-specific rules in agent prompts.

## Project Thesis

- What the system is:
- What the system is not:
- Why this project should exist:
- Authoritative source, substrate, or real-world boundary the system must respect:

## Desired User Outcomes

- Primary users or operators:
- Highest-value workflow:
- What the user should be able to do:
- What the user should be able to inspect, verify, or understand:
- What would make the result feel genuinely useful rather than merely plausible:

## Non-Goals

- Do not build:
- Do not fake via scaffolding, fixtures, mocks, dry runs, or structure alone:
- Do not smooth over ambiguity, uncertainty, or missing evidence with polished wording:
- Do not preserve legacy behavior, donor-code assumptions, or compatibility shims unless explicitly required:

## Architectural Shape

- Required runtime surfaces or layers:
- Required source/evidence boundaries:
- Required inspectability surfaces:
- External systems, providers, or storage assumptions:
- Forbidden or deferred surfaces:
- First honest vertical slice that would prove the direction:

## Runtime and Implementation Discipline

- What must exist as real runtime behavior:
- What counts as meaningful progress:
- What must be visible before synthesis, automation, or UX claims are trusted:
- Approval-sensitive surfaces:
- Downstream fixtures, samples, or dependent roles that must remain truthful:

## Project Quality Bar

- UX qualities the system must preserve:
- Evidence, provenance, or citation expectations:
- Retrieval, orchestration, or runtime inspectability expectations:
- Verification expectations:
- Operator expectations, especially for novice users:

## Acceptance Probes

Repeat this block as needed for the probes that define real progress.

- Probe name:
- User-facing question it answers:
- Minimum real runtime path it must exercise:
- Evidence that should be inspectable or saved:
- What does not count as proof:

## Open Questions To Clarify When They Matter

- Decision that would materially change the next implementation directive:
- Safe corpus, dataset, or sample for early probes:
- External-call, privacy, mutation, or deployment constraints:
- First interface surface to prove:
- Unknown that is acceptable to defer for now:

## Project References

- Companion governance primitives doc:
- Other project-spec docs in this folder:
