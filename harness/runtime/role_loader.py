from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib


@dataclass(frozen=True)
class RoleConfig:
    role_id: str
    name: str
    mode: str
    model: str
    instructions_path: Path
    instructions: str
    output_schema_path: Path
    may_read_files: bool
    may_write_files: bool
    may_run_shell: bool
    may_call_workers: bool


def load_role(manifest_path: Path) -> RoleConfig:
    manifest_path = manifest_path.resolve()
    data = _load_toml(manifest_path)

    agent = _section(data, "agent")
    return_contract = _section(data, "return_contract")
    permissions = _section(data, "permissions")

    instructions_path = _resolve_existing_path(
        manifest_path, _required_str(agent, "instructions_path")
    )
    output_schema_path = _resolve_existing_path(
        manifest_path, _required_str(return_contract, "output_schema")
    )

    config = RoleConfig(
        role_id=_required_str(agent, "id"),
        name=_required_str(agent, "name"),
        mode=_required_str(agent, "mode"),
        model=_required_str(agent, "model"),
        instructions_path=instructions_path,
        instructions=instructions_path.read_text(encoding="utf-8"),
        output_schema_path=output_schema_path,
        may_read_files=_required_bool(permissions, "may_read_files"),
        may_write_files=_required_bool(permissions, "may_write_files"),
        may_run_shell=_required_bool(permissions, "may_run_shell"),
        may_call_workers=_required_bool(permissions, "may_call_workers"),
    )
    _validate_read_only_role(config)
    return config


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Role manifest not found: {path}")
    with path.open("rb") as file:
        return tomllib.load(file)


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"Missing TOML section [{name}]")
    return value


def _required_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required string field: {key}")
    return value


def _required_bool(section: dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"Missing required boolean field: {key}")
    return value


def _resolve_existing_path(manifest_path: Path, relative_path: str) -> Path:
    resolved = (manifest_path.parent / relative_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(
            f"Configured path does not exist: {relative_path} resolved to {resolved}"
        )
    return resolved


def _validate_read_only_role(config: RoleConfig) -> None:
    if config.mode != "read_only_report":
        raise ValueError(f"Unsupported role mode for first slice: {config.mode}")
    if config.may_write_files:
        raise ValueError("Project Manager role may not write files in the first slice.")
    if config.may_run_shell:
        raise ValueError("Project Manager role may not run shell commands in the first slice.")
    if config.may_call_workers:
        raise ValueError("Project Manager role may not call workers in the first slice.")
