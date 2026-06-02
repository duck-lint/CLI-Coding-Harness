from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from harness.context.context_compiler import compile_context_packet
from harness.contracts import ProjectManagerReport, TaskBrief
from harness.runtime.agent_callers import call_project_manager
from harness.runtime.role_loader import load_role


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "plan":
        return asyncio.run(_run_plan(args.task_text))
    parser.print_help()
    return 1


async def _run_plan(task_text: str) -> int:
    repo_root = _repo_root()
    _load_local_openai_key(repo_root / ".env.local")
    _require_openai_key()

    role = load_role(repo_root / "harness" / "agents" / "project-manager.toml")
    context_packet = compile_context_packet(task_text, repo_root)
    run_id = _timestamp()
    run_dir = repo_root / "harness" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    task_brief = TaskBrief(
        task_text=task_text,
        created_at=datetime.now(UTC),
        role_id=role.role_id,
        role_name=role.name,
        mode=role.mode,
        run_id=run_id,
        context_sources=context_packet.sources,
    )

    _write_json(run_dir / "task_brief.json", task_brief)
    (run_dir / "context_packet.md").write_text(context_packet.markdown, encoding="utf-8")

    report = await call_project_manager(role, context_packet.markdown)
    _write_json(run_dir / "project_manager_report.json", report)
    _print_summary(run_dir, role.name, report)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m harness.runtime.orchestrator",
        description="Run the local coding-agent harness orchestrator.",
    )
    subparsers = parser.add_subparsers(dest="command")
    plan = subparsers.add_parser(
        "plan",
        help="Run the read-only Project Manager report slice.",
    )
    plan.add_argument("task_text", help="Task text to review.")
    return parser


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _load_local_openai_key(path: Path) -> None:
    if os.environ.get("OPENAI_API_KEY") or not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "OPENAI_API_KEY" and value.strip():
            os.environ["OPENAI_API_KEY"] = value.strip().strip('"').strip("'")
            return


def _require_openai_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required before calling the Project Manager.")


def _write_json(path: Path, model: TaskBrief | ProjectManagerReport) -> None:
    path.write_text(
        json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _print_summary(run_dir: Path, role_name: str, report: ProjectManagerReport) -> None:
    print(f"Route: {role_name}")
    print(f"Status: {report.status}")
    print(f"Run: {run_dir}")
    print(f"Summary: {report.summary}")
    print(f"Next admissible transition: {report.next_admissible_transition}")


if __name__ == "__main__":
    raise SystemExit(main())
