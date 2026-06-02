# Project Spec

This project is a local Python CLI harness for orchestrating clean-context coding agents through the OpenAI Agents SDK.

It is not a chatbot UI, autonomous repo mutator, generic RAG system, or replacement for project-specific specs.

The system exists to make agent-assisted coding inspectable, governed, and reproducible by separating role prompts, context packets, structured reports, deterministic routing, worker adapters, and archived run artifacts.

The first honest vertical slice is:

`python -m harness.runtime.orchestrator plan "TASK TEXT"`

This must load `harness/agents/project-manager.agent.json`, compile a structured context packet, call the Project Manager through the OpenAI Agents SDK, validate the structured report, save `task_brief.json`, `context_packet.json`, and `project_manager_report.json` under `harness/runs/`, print a short summary, and stop before implementation.
