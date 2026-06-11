from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class GitContext(BaseModel):
  model_config = ConfigDict(extra="forbid")

  available: bool
  branch: str | None = None
  commit: str | None = None
  is_dirty: bool | None = None
  status_summary: list[str] = Field(default_factory=list)
  failure: str | None = None


def _run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
  return subprocess.run(
    ["git", *args],
    cwd=repo_root,
    capture_output=True,
    text=True,
    check=False,
    timeout=10,
  )


def collect_git_context(repo_root: Path) -> GitContext:
  try:
    inside_work_tree = _run_git(repo_root, "rev-parse", "--is-inside-work-tree")
  except (OSError, subprocess.SubprocessError) as error:
    return GitContext(available=False, failure=str(error))

  if (
    inside_work_tree.returncode != 0
    or inside_work_tree.stdout.strip() != "true"
  ):
    failure = inside_work_tree.stderr.strip() or "Directory is not a git worktree."
    return GitContext(available=False, failure=failure)

  try:
    branch_result = _run_git(repo_root, "branch", "--show-current")
    commit_result = _run_git(repo_root, "rev-parse", "HEAD")
    status_result = _run_git(repo_root, "status", "--porcelain=v1")
  except (OSError, subprocess.SubprocessError) as error:
    return GitContext(available=False, failure=str(error))

  failed_commands = [
    result.stderr.strip()
    for result in (branch_result, commit_result, status_result)
    if result.returncode != 0
  ]
  if failed_commands:
    return GitContext(
      available=False,
      failure="; ".join(message for message in failed_commands if message),
    )

  status_summary = [
    line for line in status_result.stdout.splitlines() if line.strip()
  ]
  return GitContext(
    available=True,
    branch=branch_result.stdout.strip() or None,
    commit=commit_result.stdout.strip() or None,
    is_dirty=bool(status_summary),
    status_summary=status_summary,
  )
