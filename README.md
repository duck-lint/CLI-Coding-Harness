work in progress

working on compilers for API response calls

custom CLI agent harness for API calls
  constructed on semantic geometry.
    Hard typed but flexible, 
    every line earns it's keep.

reference repo: https://github.com/duck-lint/coding-agent-harness
turning the custom agent `.md`'s into CLI agents

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
