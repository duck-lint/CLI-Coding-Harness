from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import subprocess

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


@dataclass(frozen=True)
class ContextPacket:
    """
    Authoritative context packet for a role call.

    `payload` is the canonical semantic object.
    JSON is the preferred format sent to the model and saved as runtime evidence.
    """

    payload: dict[str, Any]

    @property
    def sources(self) -> list[str]:
        included = self.payload.get("authority_manifest", {}).get("included_sources", [])
        return [source["path"] for source in included if "path" in source]

    def to_json_text(self) -> str:
        return json.dumps(self.payload, indent=2, ensure_ascii=False, sort_keys=False)


def compile_context_packet(task_text: str, repo_root: Path) -> ContextPacket:
    """
    Build a structured Project Manager context packet.

    Runtime owns file inspection and context compilation.
    The Project Manager receives this packet and must not inspect files directly.
    """

    repo_root = repo_root.resolve()

    included_sources: list[dict[str, Any]] = []
    missing_sources: list[dict[str, Any]] = []

    packet: dict[str, Any] = {
        "packet_type": "project_manager_context_packet",
        "version": "0.1.0",
        "task": {
            "text": task_text.strip()
        },
        "repo": {
            "root": str(repo_root),
            "harness_root": _relative_label(repo_root / "harness", repo_root),
            "git_status_short": _git_status(repo_root)
        },
        "authority_manifest": {
            "included_sources": included_sources,
            "missing_sources": missing_sources
        },
        "authority_sources": {},
        "probe_evidence": {
            "available": False,
            "items": []
        }
    }

    source_specs = [
        {
            "id": "project_spec",
            "label": "Project Spec",
            "candidates": [
                repo_root / "harness" / "project-spec" / "project-spec.json",
                repo_root / "harness" / "project-spec" / "project-spec.md"
            ],
            "required": True
        },
        {
            "id": "governance_primitives",
            "label": "Governance Primitives",
            "candidates": [
                repo_root / "harness" / "project-spec" / "governance-primitives.json",
                repo_root / "harness" / "project-spec" / "governance-primitives.md"
            ],
            "required": True
        },
        {
            "id": "runtime_contract",
            "label": "Runtime Contract",
            "candidates": [
                repo_root / "harness" / "policies" / "runtime-contract.json",
                repo_root / "harness" / "policies" / "runtime-contract.md"
            ],
            "required": True
        },
        {
            "id": "runtime_budget",
            "label": "Runtime Budget",
            "candidates": [
                repo_root / "harness" / "policies" / "runtime-budget.json",
                repo_root / "harness" / "policies" / "runtime-budget.toml"
            ],
            "required": False
        },
        {
            "id": "open_decisions",
            "label": "Open Decisions",
            "candidates": [
                repo_root / "harness" / "project-spec" / "open-decisions.json",
                repo_root / "harness" / "project-spec" / "open-decisions.md",
                repo_root / "harness" / "open-decisions.json",
                repo_root / "harness" / "open-decisions.md"
            ],
            "required": False
        },
        {
            "id": "known_failures",
            "label": "Known Failures",
            "candidates": [
                repo_root / "harness" / "project-spec" / "known-failures.json",
                repo_root / "harness" / "project-spec" / "known-failures.md",
                repo_root / "harness" / "known-failures.json",
                repo_root / "harness" / "known-failures.md"
            ],
            "required": False
        }
    ]

    for spec in source_specs:
        _add_source_from_candidates(
            packet,
            source_id=spec["id"],
            label=spec["label"],
            candidates=spec["candidates"],
            repo_root=repo_root,
            required=spec["required"]
        )

    return ContextPacket(payload=packet)


def write_context_artifacts(packet: ContextPacket, run_dir: Path) -> None:
    """
    Save context packet artifacts for a run.

    `context_packet.json` is authoritative.
    """

    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "context_packet.json").write_text(
        packet.to_json_text() + "\n",
        encoding="utf-8"
    )


def _add_source_from_candidates(
    packet: dict[str, Any],
    *,
    source_id: str,
    label: str,
    candidates: list[Path],
    repo_root: Path,
    required: bool
) -> None:
    existing_path = next((path for path in candidates if path.exists()), None)

    if existing_path is None:
        candidate_labels = [_relative_label(path, repo_root) for path in candidates]
        _record_missing_source(
            packet,
            source_id=source_id,
            label=label,
            candidate_paths=candidate_labels,
            required=required
        )

        if required:
            joined = ", ".join(candidate_labels)
            raise FileNotFoundError(f"Required context source missing for {source_id}: {joined}")

        return

    _add_source(
        packet,
        source_id=source_id,
        label=label,
        path=existing_path,
        repo_root=repo_root,
        required=required
    )


def _add_source(
    packet: dict[str, Any],
    *,
    source_id: str,
    label: str,
    path: Path,
    repo_root: Path,
    required: bool
) -> None:
    source_path = _relative_label(path, repo_root)
    content_type = _guess_content_type(path)
    raw_text = path.read_text(encoding="utf-8")

    content = _parse_source_content(
        raw_text=raw_text,
        content_type=content_type,
        path=path
    )

    packet["authority_manifest"]["included_sources"].append({
        "id": source_id,
        "label": label,
        "path": source_path,
        "required": required,
        "status": "included",
        "content_type": content_type
    })

    packet["authority_sources"][source_id] = {
        "id": source_id,
        "label": label,
        "path": source_path,
        "content_type": content_type,
        "content": content
    }


def _record_missing_source(
    packet: dict[str, Any],
    *,
    source_id: str,
    label: str,
    candidate_paths: list[str],
    required: bool
) -> None:
    packet["authority_manifest"]["missing_sources"].append({
        "id": source_id,
        "label": label,
        "candidate_paths": candidate_paths,
        "required": required,
        "status": "missing"
    })


def _parse_source_content(*, raw_text: str, content_type: str, path: Path) -> Any:
    """
    Preserve structured sources as structured objects.

    Markdown/plain text remain strings.
    JSON becomes dict/list/scalar.
    TOML becomes dict when tomllib is available.
    """

    if content_type == "application/json":
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in context source {path}: {exc}") from exc

    if content_type == "application/toml":
        if tomllib is None:
            return {
                "parse_status": "unparsed",
                "reason": "tomllib unavailable; Python 3.11+ required for TOML parsing without dependency",
                "raw_text": raw_text
            }

        try:
            return tomllib.loads(raw_text)
        except tomllib.TOMLDecodeError as exc:  # type: ignore[union-attr]
            raise ValueError(f"Invalid TOML in context source {path}: {exc}") from exc

    return raw_text


def _git_status(repo_root: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            capture_output=True,
            check=False,
            text=True,
            timeout=10
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "available": False,
            "status": "unavailable",
            "detail": str(exc),
            "short": "",
            "clean": None
        }

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return {
            "available": False,
            "status": "failed",
            "detail": detail or "git status failed",
            "short": "",
            "clean": None
        }

    short_status = result.stdout.strip()

    return {
        "available": True,
        "status": "ok",
        "detail": "",
        "short": short_status,
        "clean": not bool(short_status)
    }


def _guess_content_type(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == ".json":
        return "application/json"

    if suffix == ".md":
        return "text/markdown"

    if suffix == ".toml":
        return "application/toml"

    if suffix == ".txt":
        return "text/plain"

    return "text/plain"


def _relative_label(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return str(path.resolve())
