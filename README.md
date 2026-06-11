work in progress

current implementation seam: compilers for API response calls

# Coding Agent CLI Harness

**Hard-typed, but flexible. Every line earns its keep.**

This harness defines a typed semantic state substrate: user input is parsed into control signals, and those controls determine which operations are allowed over the current project state.

The goal is not to make an LLM “act like” a project manager, planner, reviewer, or implementer. The goal is to make project state explicit, validate every transition, and use model calls only as bounded operators inside a governed workflow.

The agent is not the system. The system is the governed recurrence between typed state, control input, validated transition, and feedback.
reference repo: https://github.com/duck-lint/coding-agent-harness


## Provider-neutral compiler scripts

```powershell
python harness/project_spec/static_context_packet_compiler.py
```

This scaffold is currently exposed through directly executable compiler scripts,
not through the package CLI.

Compiles global harness governance and repo-local static/operational state into
`static_context_packet.json`.

```powershell
python harness/agents/agent_context_compiler.py --agent harness/agents/project_manager.agent.json
```

Compiles the selected agent contract plus inputs declared by that agent's
`agent_input_policy` into `agent_context_packet.json`. For PM,
`static_context_packet` is resolved because the PM agent policy declares it.

Build a provider-neutral API call packet for a direct task:

```powershell
python harness/runtime/api_call_packet_builder.py --task "Review the current project trajectory." --direct
```

Build a provider-neutral API call packet for a direct task with explicit static
context attached as supplementary context:

```powershell
python harness/runtime/api_call_packet_builder.py --task "Review the current project trajectory." --direct --static-context harness/runs/static_context_packet.json
```

Build a provider-neutral API call packet for an agent-routed task:

```powershell
python harness/runtime/api_call_packet_builder.py --task "Review the current project trajectory." --agent harness/agents/project_manager.agent.json
```

Resolve effective model selection:

```powershell
python harness/runtime/model_resolution.py --api-call-packet harness/runs/api_call_packet.json --provider-runtime-policy harness/runtime/provider_runtime.policy.json
```

This records which provider/model would be used before provider-specific
payload rendering. Agent-routed calls use the selected agent contract model as
primary authority. Direct calls use the provider runtime policy default.
Runtime budget constrains token behavior and does not select the model.

These scripts emit the current bounded-slice artifacts:

- `static_context_packet.json`
- `agent_context_packet.json`
- `api_call_packet.json`

The package entrypoint is reserved for the real operator workflow. For now:

```powershell
python -m harness "Review the current project trajectory."
```

fails honestly because provider-specific payload rendering and model calls are
not implemented yet.
