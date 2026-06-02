from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class ContextPacket:
    markdown: str
    sources: list[str]


def compile_context_packet(task_text: str, repo_root: Path) -> ContextPacket:
    repo_root = repo_root.resolve()
    sources: list[str] = []
    sections = [
        _section("Task Text", task_text.strip()),
        _git_status_section(repo_root, sources),
        _file_section(
            "Project Spec",
            repo_root / "harness" / "project-spec" / "project-spec.md",
            repo_root,
            sources,
            required=True,
        ),
        _file_section(
            "Governance Primitives",
            repo_root / "harness" / "project-spec" / "governance-primitives.md",
            repo_root,
            sources,
            required=True,
        ),
        _file_section(
            "Known Failures",
            repo_root / "harness" / "project-spec" / "known-failures.md",
            repo_root,
            sources,
            required=True,
        ),
        _file_section(
            "Open Decisions",
            repo_root / "harness" / "project-spec" / "open-decisions.md",
            repo_root,
            sources,
            required=True,
        ),
        _file_section(
            "Runtime Contract",
            repo_root / "harness" / "policies" / "runtime-contract.md",
            repo_root,
            sources,
            required=True,
        ),
        _file_section(
            "Runtime Budget",
            repo_root / "harness" / "policies" / "runtime-budget.toml",
            repo_root,
            sources,
            required=True,
        ),
    ]
    return ContextPacket(markdown="\n\n".join(sections) + "\n", sources=sources)


def _git_status_section(repo_root: Path, sources: list[str]) -> str:
    sources.append("git status --short")
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _section("Git Status", f"Unavailable: {exc}")

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return _section("Git Status", f"Unavailable: {detail or 'git status failed'}")

    status = result.stdout.strip()
    return _section("Git Status", status or "Clean working tree.")


def _file_section(
    title: str,
    path: Path,
    repo_root: Path,
    sources: list[str],
    *,
    required: bool,
) -> str:
    label = _relative_label(path, repo_root)
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required context file missing: {label}")
        sources.append(f"{label} (missing optional)")
        return _section(title, f"Optional context source missing: {label}")

    sources.append(label)
    return _section(title, path.read_text(encoding="utf-8"))


def _section(title: str, body: str) -> str:
    return f"# {title}\n\n{body.strip()}"


def _relative_label(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return str(path.resolve())
