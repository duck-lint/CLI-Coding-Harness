from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RolePermissions:
    may_receive_context_packet: bool
    may_inspect_repo_files_directly: bool
    may_write_files: bool
    may_run_shell: bool
    may_call_workers: bool


@dataclass(frozen=True)
class ReturnContract:
    schema_path: Path
    schema: dict[str, Any]
    strict: bool


@dataclass(frozen=True)
class RoleConfig:
    role_id: str
    name: str
    mode: str
    model: str
    instructions_payload: dict[str, Any]
    context_policy: dict[str, Any]
    return_contract: ReturnContract
    permissions: RolePermissions


def load_role(manifest_path: Path) -> RoleConfig:
    manifest_path = manifest_path.resolve()
    data = _load_json(manifest_path)

    agent = _section(data, "agent")
    instructions = _section(data, "instructions")
    context_policy = _section(data, "context_policy")
    return_contract = _section(data, "return_contract")
    permissions = _section(data, "permissions")
    role_id = _required_str(agent, "id")
    default_model = _runtime_default_model(manifest_path, role_id)

    output_schema_path = _resolve_existing_path(
        manifest_path, _required_str(return_contract, "schema")
    )
    output_schema = _load_json(output_schema_path)

    config = RoleConfig(
        role_id=role_id,
        name=_required_str(agent, "name"),
        mode=_required_str(agent, "mode"),
        model=default_model,
        instructions_payload=instructions,
        context_policy=context_policy,
        return_contract=ReturnContract(
            schema_path=output_schema_path,
            schema=output_schema,
            strict=_required_bool(return_contract, "strict"),
        ),
        permissions=RolePermissions(
            may_receive_context_packet=_required_bool(permissions, "may_receive_context_packet"),
            may_inspect_repo_files_directly=_required_bool(
                permissions, "may_inspect_repo_files_directly"
            ),
            may_write_files=_required_bool(permissions, "may_write_files"),
            may_run_shell=_required_bool(permissions, "may_run_shell"),
            may_call_workers=_required_bool(permissions, "may_call_workers"),
        ),
    )
    _validate_read_only_role(config)
    return config


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Role manifest not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return data


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


def _runtime_default_model(manifest_path: Path, role_id: str) -> str:
    repo_root = _repo_root_from_manifest(manifest_path)
    budget_path = (repo_root / "harness" / "policies" / "runtime_budget.policy.json").resolve()
    budget = _load_json(budget_path)
    default = _section(budget, "default")
    overrides = default.get("agent_model_overrides", {})
    if overrides is not None and not isinstance(overrides, dict):
        raise ValueError("agent_model_overrides must be a JSON object when present.")

    if isinstance(overrides, dict):
        override = overrides.get(role_id)
        if override is not None:
            if not isinstance(override, str) or not override.strip():
                raise ValueError(
                    f"Invalid model override for {role_id}: expected non-empty string."
                )
            return override

    return _required_str(default, "default_model")


def _repo_root_from_manifest(manifest_path: Path) -> Path:
    for candidate in [manifest_path, *manifest_path.parents]:
        harness_dir = candidate / "harness"
        if harness_dir.is_dir():
            return candidate
        if candidate.name == "harness":
            return candidate.parent
    return manifest_path.parent.parent.parent


def _validate_read_only_role(config: RoleConfig) -> None:
    if config.mode != "read_only_report":
        raise ValueError(f"Unsupported role mode for first slice: {config.mode}")
    if not config.permissions.may_receive_context_packet:
        raise ValueError("Project Manager role must accept a compiled context packet.")
    if config.permissions.may_inspect_repo_files_directly:
        raise ValueError("Project Manager role may not inspect repo files directly.")
    if config.permissions.may_write_files:
        raise ValueError("Project Manager role may not write files in the first slice.")
    if config.permissions.may_run_shell:
        raise ValueError("Project Manager role may not run shell commands in the first slice.")
    if config.permissions.may_call_workers:
        raise ValueError("Project Manager role may not call workers in the first slice.")
