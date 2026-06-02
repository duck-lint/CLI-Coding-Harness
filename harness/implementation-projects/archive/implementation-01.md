Acceptance Probe: first-pm-plan-slice

Command:
python -m harness.runtime.orchestrator plan "Assess whether the first PM slice is admissible"

Observed:
- Routed to Project Manager
- Returned machine-readable admissibility status
- Created run directory under harness/runs/20260602T030007Z
- Deterministic probe passed
- Stopped before planner/adversary/implementer/reviewer/archive

Result:
First PM slice is live-wired at the scaffold/runtime level. Spec-level admissibility remains conditional on the bounded first-slice scope; broader implementation claims are not yet authorized.
