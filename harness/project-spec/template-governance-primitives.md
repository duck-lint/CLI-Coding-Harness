# Governance Primitives

This file defines project-local authority semantics, approval boundaries, admissible transformations, and review scaffolding.

It is part of the project spec's invariant space. Use it to describe what implementation must preserve or explicitly amend, not to restate harness workflow prompts.

## Governance Posture

- Hard constraints the implementation must preserve:
- Observability scaffolding used to inspect those constraints:
- Distinctions that must remain explicit rather than hidden in prompts, chat history, or model intuition:

## Invariant Authority

Use this order when deciding what the project is allowed to become:

1. Explicit amendments to the project spec or governance primitives approved by project authority.
2. This file and the other docs under `harness/project-spec/**`.
3. Open decisions that interpret the project spec without silently overriding it.
4. Active plans and trackers implementing an already-authorized objective.
5. Current user instructions selecting, sequencing, or pausing already-authorized work.
6. Archived implementation history and prior chat context.

Current instructions may choose work or explicitly amend the spec, but they do not silently override project invariants.

## Task Authority

Use this order when deciding what to do next inside the current invariant space:

1. Current user instruction for the present task.
2. Open decisions in `harness/open-decisions.md`.
3. Active implementation plan and tracker.
4. Relevant repo-local harness docs under `harness/`.
5. Archived implementation history and prior chat context.

If task authority conflicts with invariant authority, stop and surface the conflict instead of improvising around it.

## Approval Boundaries

Require explicit approval before crossing:

- Project spec or governance amendment:
- Schema:
- API:
- Auth:
- Storage:
- Deployment:
- Destructive operation:
- Broad architecture:
- Compatibility or fallback commitment:
- Project-intent-dependent behavior not already authorized by the project spec:

## Invariants and Integrity Constraints

- Project truths that must remain stable:
- Authoritative versus derived, operational, synthesized, or presentation material:
- Fixture, sample, or test roles that must remain truthful:
- Compatibility promises, if any:
- Verification duties that must not be skipped:
- Unknowns, ambiguity, or uncertainty that must remain visible:

## Admissible Transformations

- Changes allowed without amending the project spec:
- Changes that require an open decision before proceeding:
- Changes that require explicit project-spec or governance amendment:
- Transformations that must preserve provenance, inspectability, or lineage:
- Transformations that are forbidden shortcuts:

## Review Checkpoints

- What should be visible before trusting source authority:
- What should be visible before trusting derived or operational evidence:
- What should be visible before trusting synthesis, automation, or UX claims:
- What should be visible before closing work as complete:

## Acceptance Probes

Repeat this block as needed for the probes that demonstrate real project progress.

- Probe name:
- Question it answers:
- Required real runtime path:
- Evidence that must be inspectable or saved:
- What does not count as proof:

## Admissibility Inputs For Harness Work

When the harness needs a strict admissibility report, derive it from this file and the rest of `harness/project-spec/**` by naming:

- Invariant constraints:
- Task constraints:
- Constraint conflicts:
- Allowed transformation types:
- Affected surfaces:
- Non-affected surfaces:
- Admissibility checks:
- Stop conditions:
