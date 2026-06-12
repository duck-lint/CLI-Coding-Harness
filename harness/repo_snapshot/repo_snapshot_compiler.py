from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
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
DEFAULT_EXCLUSIONS = [
  ".git/**",
  ".pytest_cache/**",
  "**/__pycache__/**",
  "**/*.pyc",
  "harness/**",
]


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


def _classify_exclusion(
  path: str,
  *,
  effective_exclusions: list[str],
) -> tuple[str, str] | None:
  for pattern in effective_exclusions:
    if _matches_pattern(path, pattern):
      if pattern == "harness/**":
        return "harness_excluded", pattern
      return "excluded_path", pattern

  return None


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
) -> tuple[list[str], list[OmittedRepoSnapshotFile]]:
  omitted: list[OmittedRepoSnapshotFile] = []

  if mode == "all_admissible":
    return sorted(admissible_paths), omitted

  candidates: set[str] = set()

  if mode == "paths":
    for requested_path in requested_paths:
      candidate = (repo_root / requested_path).resolve()
      relative_path = _repo_relative_path(candidate, repo_root)
      if relative_path is None:
        omitted.append(
          OmittedRepoSnapshotFile(
            path=requested_path,
            reason="outside_repo",
            detail="Requested path resolves outside repo root.",
          )
        )
        continue

      if not candidate.is_file():
        omitted.append(
          OmittedRepoSnapshotFile(
            path=relative_path,
            reason="not_found",
            detail="Requested path was not found as a file.",
          )
        )
        continue

      candidates.add(relative_path)

  if mode == "globs":
    for requested_glob in requested_globs:
      for candidate in repo_root.glob(requested_glob):
        if not candidate.is_file():
          continue
        relative_path = _repo_relative_path(candidate, repo_root)
        if relative_path is not None:
          candidates.add(relative_path)

  return sorted(candidates), omitted


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
    for pattern in DEFAULT_EXCLUSIONS
    if not (include_harness and pattern == "harness/**")
  ]
  effective_exclusions.extend(extra_exclusions)

  admissible_paths, gitignore_respected = _git_ls_files(repo_root)
  if not gitignore_respected:
    admissible_paths = _all_files_fallback(repo_root)

  candidate_paths, omitted_files = _requested_candidates(
    repo_root=repo_root,
    mode=mode,
    requested_paths=requested_paths,
    requested_globs=requested_globs,
    admissible_paths=admissible_paths,
  )

  included_files: list[RepoSnapshotFile] = []
  total_included_bytes = 0

  for relative_path in candidate_paths:
    classification = _classify_exclusion(
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
      omitted_files.append(
        OmittedRepoSnapshotFile(
          path=relative_path,
          reason="read_error",
          detail=str(error),
        )
      )
      continue

    if len(file_bytes) > max_file_bytes:
      omitted_files.append(
        OmittedRepoSnapshotFile(
          path=relative_path,
          reason="too_large",
          detail=(
            f"File size {len(file_bytes)} exceeds max_file_bytes "
            f"{max_file_bytes}."
          ),
        )
      )
      continue

    if total_included_bytes + len(file_bytes) > max_total_bytes:
      omitted_files.append(
        OmittedRepoSnapshotFile(
          path=relative_path,
          reason="too_large",
          detail=(
            "Including this file would exceed max_total_bytes "
            f"{max_total_bytes}."
          ),
        )
      )
      continue

    try:
      content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
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
