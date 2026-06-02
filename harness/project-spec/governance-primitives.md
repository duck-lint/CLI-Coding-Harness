{
  "file": "Governance Primitives"
  "context": 

This document defines the local authority boundaries for the harness runtime.
It is specific to this repository: a local Python CLI harness that orchestrates
clean-context coding agents through the OpenAI Agents SDK.

## Invariant Authority

Invariant authority lives in `harness/project-spec/**` and `harness/policies/runtime-contract.md`.
It defines what the project is allowed to become and what the harness runtime
must preserve.

The invariants for this repository are:

- The harness is a local Python CLI for orchestrating coding agents through the OpenAI Agents SDK.
- The harness is inspectable, governed, and reproducible through role prompts, context packets, structured reports, deterministic routing, worker adapters, and archived run artifacts.
- The first honest vertical slice is `python -m harness.runtime.orchestrator plan "TASK TEXT"`.
- The first slice must remain read-only, stop before implementation, and keep agent behavior bounded to the Project Manager route.
- Runtime behavior claims require explicit acceptance probes and must be classified as scaffold-only until runtime evidence exists.
- `harness/` is the canonical repo-local memory and authority surface for this project.

## Task Authority

Task authority selects and sequences work inside the invariant space.

For this repository, task authority comes from:

- the current user request;
- the current implementation plan, when present;
- open decisions, when present;
- the active repo state observed in `harness/`;
- the current PM admissibility report.

Task authority may choose among admissible transformations, but it may not:

- redefine project intent;
- invent new governance rules;
- invent acceptance criteria;
- override invariant authority;
- extend the current slice beyond its approved boundary.

## Approval Boundaries

The following changes require explicit approval because they cross an authority boundary:

- Schema changes: any modification to report contracts, JSON schema files, or typed output shapes that changes the PM report contract or task-brief contract.
- Storage and artifact layout: any change to `harness/runs/<timestamp>/` naming, file set, file format, or artifact placement.
- API or model behavior: any change to the OpenAI Agents SDK call path, model choice, structured-output semantics, retry policy, or environment-variable contract.
- Worker adapters: any addition or invocation of planner, adversary, reviewer, implementer, archivist, Codex adapters, or any new worker integration.
- File-writing permissions: any runtime write outside `harness/runs/<timestamp>/` or any agent write permission beyond the orchestrator’s local artifact save path.
- Implementation beyond the `plan` slice: any step that proceeds from planning into implementation, mutation, or multi-agent delegation.
- Compatibility commitments: any promise to preserve old paths, legacy behavior, or compatibility shims not explicitly required by the project spec.

## Admissible Transformations for the First Slice

Within the first vertical slice, admissible transformations are limited to:

- loading the Project Manager role manifest from `harness/agents/project-manager.agent.json`;
- resolving the return-contract schema path relative to the JSON agent file location;
- loading or defining the `ProjectManagerReport` contract;
- compiling a minimal context packet from the task text, `git status --short` when available, `harness/project-spec/project-spec.md`, optional `harness/project-spec/governance-primitives.md`, and `harness/policies/runtime-contract.md`;
- calling exactly one Project Manager agent through the OpenAI Agents SDK;
- validating the returned structured report;
- writing only `task_brief.json`, `project_manager_report.json`, and `context_packet.json` under `harness/runs/<timestamp>/`;
- printing a short terminal summary;
- stopping before planner, adversary, reviewer, implementer, archivist, or Codex worker execution.

The runtime may use `git status --short` directly for context collection.
The runtime may not run arbitrary shell commands for the first slice.

## Stop Conditions

Stop immediately if any of the following occurs:

- the requested change would expand beyond the `plan` slice;
- the requested change requires inventing governance primitives, acceptance criteria, or project intent not present in `harness/project-spec/**`;
- the requested change would allow file writes outside `harness/runs/<timestamp>/`;
- the requested change would invoke a worker adapter or non-PM agent;
- the requested change would alter the PM report contract without explicit approval;
- the runtime cannot validate the PM report;
- the runtime cannot produce the three required run artifacts;
- the runtime cannot preserve read-only behavior for the agent path.

## First Acceptance Probe

The first acceptance probe for this repository is:

```text
python -m harness.runtime.orchestrator plan "TASK TEXT"
```

The probe passes only if all of the following are true:

- the command loads `harness/agents/project-manager.agent.json`;
- the command compiles a context packet from the task text, repo status when available, `harness/project-spec/project-spec.md`, optional `harness/project-spec/governance-primitives.md`, and `harness/policies/runtime-contract.md`;
- the command calls only the Project Manager through the OpenAI Agents SDK;
- the command validates the returned `ProjectManagerReport`;
- the command writes `task_brief.json`, `project_manager_report.json`, and `context_packet.json` under `harness/runs/<timestamp>/`;
- the command prints a short summary;
- the command stops without entering planner, adversary, reviewer, implementer, archivist, or Codex execution.

If the probe cannot run, the missing basis must be named explicitly and the claim must remain scaffold-only.
