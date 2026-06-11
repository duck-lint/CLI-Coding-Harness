work in progress

current implementation seam: compilers for API response calls

# Coding Agent CLI Harness

**Hard-typed, but flexible. Every line earns its keep.**

This harness defines a typed semantic state substrate: user input is parsed into control signals, and those controls determine which operations are allowed over the current project state.

The goal is not to make an LLM “act like” a project manager, planner, reviewer, or implementer. The goal is to make project state explicit, validate every transition, and use model calls only as bounded operators inside a governed workflow.

The agent is not the system. The system is the governed recurrence between typed state, control input, validated transition, and feedback.
