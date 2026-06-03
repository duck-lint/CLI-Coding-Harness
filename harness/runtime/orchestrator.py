from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from harness.context.context_compiler import compile_context_packet, write_context_artifacts
from harness.contracts import ProjectManagerReport, TaskBrief
from harness.runtime.agent_callers import call_project_manager
from harness.runtime.role_loader import load_role


@dataclass(frozen=True)
class ProbeResult:
    passed: bool
    checks: list[str]
    missing_basis: list[str]

    @property
    def reason(self) -> str | None:
        if not self.missing_basis:
            return None
        return "; ".join(self.missing_basis)


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

    role = load_role(repo_root / "harness" / "agents" / "project_manager.agent.json")
    context_packet = compile_context_packet(task_text, repo_root)
    context_packet_json = context_packet.to_json_text()
    run_id = _timestamp()
    run_dir = repo_root / "harness" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    _enforce_context_budget(role, context_packet_json)

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
    write_context_artifacts(context_packet, run_dir)

    report = await call_project_manager(role, context_packet_json)
    _write_json(run_dir / "project_manager_report.json", report)
    probe_result = verify_plan_probe(run_dir, report)
    _print_summary(run_dir, role.name, report, probe_result)
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


def _enforce_context_budget(role, context_packet_json: str) -> None:
    policy = role.context_policy
    max_context_packet_tokens = int(policy.get("max_context_packet_tokens", 0))
    reserved_output_tokens = int(policy.get("reserved_output_tokens", 0))
    oversize_strategy = str(policy.get("oversize_strategy", "fail_or_batch"))
    truncation = str(policy.get("truncation", "disabled"))

    if truncation != "disabled":
        raise RuntimeError(f"Context truncation must be disabled; got {truncation!r}.")

    estimated_tokens = estimate_token_count(context_packet_json)
    if estimated_tokens <= max_context_packet_tokens:
        return

    if oversize_strategy == "fail_or_batch":
        raise RuntimeError(
            "Context packet exceeds the configured token budget "
            f"({estimated_tokens} > {max_context_packet_tokens}); batching is not implemented yet. "
            f"Reserved output tokens remain {reserved_output_tokens}."
        )

    raise RuntimeError(
        "Context packet exceeds the configured token budget and the oversize strategy is "
        f"not supported: {oversize_strategy!r}."
    )


def estimate_token_count(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _write_json(path: Path, model: TaskBrief | ProjectManagerReport) -> None:
    path.write_text(
        json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def verify_plan_probe(run_dir: Path, report: ProjectManagerReport) -> ProbeResult:
    required_files = [
        run_dir / "task_brief.json",
        run_dir / "project_manager_report.json",
        run_dir / "context_packet.json",
    ]
    checks: list[str] = []
    missing_basis: list[str] = []
    report_path = run_dir / "project_manager_report.json"

    for path in required_files:
        if not path.exists() or not path.is_file():
            missing_basis.append(str(path))
            checks.append(f"missing: {path.name}")
        else:
            checks.append(f"present: {path.name}")

    task_brief_path = run_dir / "task_brief.json"
    try:
        TaskBrief.model_validate_json(task_brief_path.read_text(encoding="utf-8"))
        checks.append("task_brief.json validates")
    except Exception as exc:  # pragma: no cover - defensive probe guard
        missing_basis.append(f"task_brief.json validation failed: {exc}")

    report_text = report_path.read_text(encoding="utf-8")
    written_report: ProjectManagerReport | None = None
    try:
        written_report = ProjectManagerReport.model_validate_json(report_text)
        checks.append("project_manager_report.json validates")
    except Exception as exc:  # pragma: no cover - defensive probe guard
        missing_basis.append(f"project_manager_report.json validation failed: {exc}")

    if written_report is not None:
        if report.model_dump(mode="json") != written_report.model_dump(mode="json"):
            missing_basis.append("in-memory report and written report diverged")
        else:
            checks.append("written report matches in-memory report")

    context_packet_path = run_dir / "context_packet.json"
    try:
        json.loads(context_packet_path.read_text(encoding="utf-8"))
        checks.append("context_packet.json parses")
    except Exception as exc:  # pragma: no cover - defensive probe guard
        missing_basis.append(f"context_packet.json parse failed: {exc}")

    if report.status in {"admissible", "admissibility-blocked"}:
        checks.append(f"report status recorded: {report.status}")

    return ProbeResult(passed=not missing_basis, checks=checks, missing_basis=missing_basis)


def _print_summary(
    run_dir: Path,
    role_name: str,
    report: ProjectManagerReport,
    probe_result: ProbeResult,
) -> None:
    print(f"Route: {role_name}")
    print(f"Status: {report.status}")
    print(f"Run: {run_dir}")
    if probe_result.passed:
        print("Probe: passed")
    else:
        print(f"Probe: failed: {probe_result.reason}")
    print(f"Summary: {report.summary}")
    print(f"Next admissible transition: {report.next_admissible_transition}")


if __name__ == "__main__":
    raise SystemExit(main())
