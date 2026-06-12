from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

# Support direct execution from harness/repo_snapshot while preserving package imports.
if __package__ in {None, ""}:
  sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pydantic import ValidationError

from harness.repo_snapshot.repo_snapshot_packet import (
  OmittedRepoSnapshotFile,
  RepoSnapshotFile,
  RepoSnapshotPacket,
  RepoSnapshotPacketMetadata,
  RepoSnapshotSelection,
  RepoSnapshotSummary,
  SnapshotMode,
)


DEFAULT_MAX_FILE_BYTES = 100_000
DEFAULT_MAX_TOTAL_BYTES = 1_000_000
DEFAULT_HARD_EXCLUSIONS = [
  ".git/**",
]
DEFAULT_SOFT_EXCLUSIONS = [
  ".pytest_cache/**",
  "**/__pycache__/**",
  "**/*.pyc",
  "harness/**",
]


@dataclass(slots=True)
class RequestedRepoSnapshotCandidate:
  path: str
  explicit_requested_path: bool


class RepoSnapshotCompilationError(RuntimeError):
  pass


def _write_json(path: Path, data: dict[str, Any]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", encoding="utf-8") as file:
    json.dump(data, file, indent=2)
    file.write("\n")


def _load_json(path: Path) -> dict[str, Any]:
  with path.open("r", encoding="utf-8") as file:
    data = json.load(file)

  if not isinstance(data, dict):
    raise TypeError(f"Expected a JSON object in {path}.")

  return data


def _normalize_pattern(pattern: str) -> str:
  normalized = pattern.replace("\\", "/").strip()
  if normalized.endswith("/"):
    return f"{normalized}**"
  return normalized


def _repo_relative_path(path: Path, repo_root: Path) -> str | None:
  try:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()
  except ValueError:
    return None


def _matches_pattern(path: str, pattern: str) -> bool:
  normalized_path = path.strip("/")
  normalized_pattern = _normalize_pattern(pattern).strip("/")
  return (
    fnmatch(normalized_path, normalized_pattern)
    or Path(normalized_path).match(normalized_pattern)
  )


def _classify_soft_exclusion(path: str, *, effective_exclusions: list[str]) -> tuple[str, str] | None:
  for pattern in effective_exclusions:
    if _matches_pattern(path, pattern):
      if pattern == "harness/**":
        return "harness_excluded", pattern
      return "excluded_path", pattern

  return None


def _is_hard_exclusion(path: str) -> bool:
  return path == ".git" or any(
    _matches_pattern(path, pattern) for pattern in DEFAULT_HARD_EXCLUSIONS
  )


def _git_ls_files(repo_root: Path) -> tuple[set[str], bool]:
  command = [
    "git",
    "-C",
    str(repo_root),
    "ls-files",
    "--cached",
    "--others",
    "--exclude-standard",
  ]
  completed = subprocess.run(
    command,
    capture_output=True,
    text=True,
    check=False,
  )
  if completed.returncode != 0:
    return set(), False

  return {
    line.strip().replace("\\", "/")
    for line in completed.stdout.splitlines()
    if line.strip()
  }, True


def _git_check_ignored(repo_root: Path, relative_path: str) -> bool:
  completed = subprocess.run(
    [
      "git",
      "-C",
      str(repo_root),
      "check-ignore",
      relative_path,
    ],
    capture_output=True,
    text=True,
    check=False,
  )
  return completed.returncode == 0


def _all_files_fallback(repo_root: Path) -> set[str]:
  return {
    path.relative_to(repo_root).as_posix()
    for path in repo_root.rglob("*")
    if path.is_file()
  }


def _requested_candidates(
  *,
  repo_root: Path,
  mode: SnapshotMode,
  requested_paths: list[str],
  requested_globs: list[str],
  admissible_paths: set[str],
) -> tuple[
  list[RequestedRepoSnapshotCandidate],
  list[OmittedRepoSnapshotFile],
  list[str],
]:
  omitted: list[OmittedRepoSnapshotFile] = []
  explicit_path_errors: list[str] = []

  if mode == "all_admissible":
    return [
      RequestedRepoSnapshotCandidate(path=path, explicit_requested_path=False)
      for path in sorted(admissible_paths)
    ], omitted, explicit_path_errors

  candidates: dict[str, RequestedRepoSnapshotCandidate] = {}

  if mode == "paths":
    for requested_path in requested_paths:
      candidate = (repo_root / requested_path).resolve()
      relative_path = _repo_relative_path(candidate, repo_root)
      if relative_path is None:
        explicit_path_errors.append(
          f"Requested path {requested_path} is outside repo root."
        )
        continue

      if _is_hard_exclusion(relative_path):
        explicit_path_errors.append(
          f"Requested path {relative_path} is hard-denied by .git exclusion."
        )
        continue

      if not candidate.exists():
        explicit_path_errors.append(
          f"Requested path {relative_path} was not found."
        )
        continue

      if candidate.is_dir():
        explicit_path_errors.append(
          f"Requested path {relative_path} is a directory, not a file."
        )
        continue

      if not candidate.is_file():
        explicit_path_errors.append(
          f"Requested path {relative_path} is not a readable file."
        )
        continue

      candidates[relative_path] = RequestedRepoSnapshotCandidate(
        path=relative_path,
        explicit_requested_path=True,
      )

  if mode == "globs":
    for requested_glob in requested_globs:
      for candidate in repo_root.glob(requested_glob):
        if not candidate.is_file():
          continue
        relative_path = _repo_relative_path(candidate, repo_root)
        if relative_path is not None:
          candidates.setdefault(
            relative_path,
            RequestedRepoSnapshotCandidate(
              path=relative_path,
              explicit_requested_path=False,
            ),
          )

  return sorted(candidates.values(), key=lambda item: item.path), omitted, explicit_path_errors


def compile_repo_snapshot_packet(
  *,
  repo_root: Path,
  output_path: Path,
  mode: SnapshotMode,
  include_harness: bool = False,
  requested_paths: list[str] | None = None,
  requested_globs: list[str] | None = None,
  exclusions: list[str] | None = None,
  max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
  max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> RepoSnapshotPacket:
  requested_paths = requested_paths or []
  requested_globs = requested_globs or []
  exclusions = exclusions or []

  repo_root = repo_root.resolve()
  output_path = output_path.resolve()
  extra_exclusions = [_normalize_pattern(pattern) for pattern in exclusions]
  effective_exclusions = [
    pattern
    for pattern in DEFAULT_SOFT_EXCLUSIONS
    if not (include_harness and pattern == "harness/**")
  ]
  effective_exclusions.extend(extra_exclusions)

  admissible_paths, gitignore_respected = _git_ls_files(repo_root)
  if not gitignore_respected:
    admissible_paths = _all_files_fallback(repo_root)

  candidate_paths, omitted_files, explicit_path_errors = _requested_candidates(
    repo_root=repo_root,
    mode=mode,
    requested_paths=requested_paths,
    requested_globs=requested_globs,
    admissible_paths=admissible_paths,
  )

  if explicit_path_errors:
    raise RepoSnapshotCompilationError(
      "Explicit repo snapshot path requests could not be satisfied: "
      + "; ".join(explicit_path_errors)
    )

  included_files: list[RepoSnapshotFile] = []
  total_included_bytes = 0

  for candidate in candidate_paths:
    relative_path = candidate.path

    if not candidate.explicit_requested_path:
      classification = _classify_soft_exclusion(
        relative_path,
        effective_exclusions=effective_exclusions,
      )
      if classification is not None:
        reason, pattern = classification
        omitted_files.append(
          OmittedRepoSnapshotFile(
            path=relative_path,
            reason=reason,
            detail=f"Matched exclusion pattern {pattern}.",
          )
        )
        continue

      if gitignore_respected and relative_path not in admissible_paths:
        if _git_check_ignored(repo_root, relative_path):
          omitted_files.append(
            OmittedRepoSnapshotFile(
              path=relative_path,
              reason="gitignored",
              detail="Excluded by .gitignore or git exclude rules.",
            )
          )
        else:
          omitted_files.append(
            OmittedRepoSnapshotFile(
              path=relative_path,
              reason="excluded_path",
              detail="Path is not admissible under repo snapshot selection.",
            )
          )
        continue

    file_path = repo_root / relative_path
    try:
      file_bytes = file_path.read_bytes()
    except OSError as error:
      if candidate.explicit_requested_path:
        raise RepoSnapshotCompilationError(
          f"Explicit repo snapshot path {relative_path} could not be read: {error}"
        ) from error
      omitted_files.append(
        OmittedRepoSnapshotFile(
          path=relative_path,
          reason="read_error",
          detail=str(error),
        )
      )
      continue

    if len(file_bytes) > max_file_bytes:
      message = (
        f"Explicit repo snapshot path {relative_path} exceeds max_file_bytes "
        f"{max_file_bytes}."
        if candidate.explicit_requested_path
        else (
          f"File size {len(file_bytes)} exceeds max_file_bytes "
          f"{max_file_bytes}."
        )
      )
      if candidate.explicit_requested_path:
        raise RepoSnapshotCompilationError(message)
      omitted_files.append(
        OmittedRepoSnapshotFile(
          path=relative_path,
          reason="too_large",
          detail=message,
        )
      )
      continue

    if total_included_bytes + len(file_bytes) > max_total_bytes:
      message = (
        f"Explicit repo snapshot path {relative_path} would exceed max_total_bytes "
        f"{max_total_bytes}."
        if candidate.explicit_requested_path
        else (
          "Including this file would exceed max_total_bytes "
          f"{max_total_bytes}."
        )
      )
      if candidate.explicit_requested_path:
        raise RepoSnapshotCompilationError(message)
      omitted_files.append(
        OmittedRepoSnapshotFile(
          path=relative_path,
          reason="too_large",
          detail=message,
        )
      )
      continue

    try:
      content = file_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
      if candidate.explicit_requested_path:
        raise RepoSnapshotCompilationError(
          f"Explicit repo snapshot path {relative_path} is not UTF-8 text."
        ) from error
      omitted_files.append(
        OmittedRepoSnapshotFile(
          path=relative_path,
          reason="binary",
          detail="File could not be decoded as UTF-8 text.",
        )
      )
      continue

    included_files.append(
      RepoSnapshotFile(
        path=relative_path,
        explicit_requested_path=candidate.explicit_requested_path,
        size_bytes=len(file_bytes),
        sha256=hashlib.sha256(file_bytes).hexdigest(),
        encoding="utf-8",
        content=content,
      )
    )
    total_included_bytes += len(file_bytes)

  packet = RepoSnapshotPacket(
    metadata=RepoSnapshotPacketMetadata(
      document_id="repo_snapshot_packet.json",
      title="Repo Snapshot Packet",
      purpose="Compiled repo file evidence selected for a model call.",
      source_format="json",
      document_authority="generated_artifact",
    ),
    selection=RepoSnapshotSelection(
      mode=mode,
      include_harness=include_harness,
      explicit_path_overrides_default_exclusions=(
        mode == "paths" and bool(requested_paths)
      ),
      repo_root=str(repo_root),
      requested_paths=requested_paths,
      requested_globs=requested_globs,
      exclusions=effective_exclusions,
      gitignore_respected=gitignore_respected,
      harness_excluded=(not include_harness and (repo_root / "harness").is_dir()),
    ),
    files=included_files,
    omitted_files=omitted_files,
    summary=RepoSnapshotSummary(
      included_count=len(included_files),
      omitted_count=len(omitted_files),
      total_included_bytes=total_included_bytes,
    ),
  )

  _write_json(output_path, packet.model_dump(mode="json"))
  return RepoSnapshotPacket.model_validate(_load_json(output_path))


def build_argument_parser() -> argparse.ArgumentParser:
  script_path = Path(__file__).resolve()
  repo_root = script_path.parents[2]
  harness_root = script_path.parents[1]

  parser = argparse.ArgumentParser(
    description="Compile a RepoSnapshotPacket artifact.",
  )
  parser.add_argument(
    "--repo-root",
    type=Path,
    default=repo_root,
    help="Root of the repo being snapshotted.",
  )
  mode_group = parser.add_mutually_exclusive_group(required=True)
  mode_group.add_argument(
    "--path",
    action="append",
    default=[],
    help="Repo-relative file path to include.",
  )
  mode_group.add_argument(
    "--glob",
    action="append",
    default=[],
    help="Repo-relative glob to include.",
  )
  mode_group.add_argument(
    "--all-admissible",
    action="store_true",
    help="Include all admissible repo files.",
  )
  parser.add_argument(
    "--exclude",
    action="append",
    default=[],
    help="Additional exclusion glob pattern.",
  )
  parser.add_argument(
    "--include-harness",
    action="store_true",
    help=(
      "Allow harness/ files into the repo snapshot. This is mainly for "
      "self-hosting meta development work."
    ),
  )
  parser.add_argument(
    "--max-file-bytes",
    type=int,
    default=DEFAULT_MAX_FILE_BYTES,
  )
  parser.add_argument(
    "--max-total-bytes",
    type=int,
    default=DEFAULT_MAX_TOTAL_BYTES,
  )
  parser.add_argument(
    "--output",
    type=Path,
    default=harness_root / "runs" / "repo_snapshot_packet.json",
    help="Destination for the emitted RepoSnapshotPacket JSON.",
  )
  return parser


def main(argv: list[str] | None = None) -> int:
  args = build_argument_parser().parse_args(argv)
  mode: SnapshotMode = (
    "all_admissible"
    if args.all_admissible
    else "paths" if args.path else "globs"
  )

  try:
    packet = compile_repo_snapshot_packet(
      repo_root=args.repo_root.resolve(),
      output_path=args.output.resolve(),
      mode=mode,
      include_harness=args.include_harness,
      requested_paths=args.path,
      requested_globs=args.glob,
      exclusions=args.exclude,
      max_file_bytes=args.max_file_bytes,
      max_total_bytes=args.max_total_bytes,
    )
  except (OSError, RepoSnapshotCompilationError, TypeError, ValidationError, ValueError) as error:
    print(f"FAIL: {error}", file=sys.stderr)
    return 1

  print(f"PASS: Repo snapshot packet written to {args.output.resolve()}")
  print(
    "Files: "
    f"{packet.summary.included_count} included, "
    f"{packet.summary.omitted_count} omitted."
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
