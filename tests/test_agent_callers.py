from __future__ import annotations

import json
import unittest
from dataclasses import asdict
from pathlib import Path

from harness.runtime.agent_callers import (
    _render_agent_instructions,
    build_effective_instruction_contract,
)
from harness.runtime.role_loader import load_role


class RenderAgentInstructionsTests(unittest.TestCase):
    def test_rendered_instructions_are_exact_json_wrapper_only(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        role = load_role(repo_root / "harness" / "agents" / "project_manager.agent.json")

        contract = build_effective_instruction_contract(role)
        expected_json = json.dumps(asdict(contract), indent=2, ensure_ascii=False)
        rendered = _render_agent_instructions(role)

        self.assertEqual(
            rendered,
            "The JSON object below is the complete effective instruction contract.\n\n"
            + expected_json,
        )

    def test_effective_contract_contains_current_obligations(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        role = load_role(repo_root / "harness" / "agents" / "project_manager.agent.json")

        contract = asdict(build_effective_instruction_contract(role))

        self.assertEqual(contract["role_instructions"], role.instructions_payload)

        source_coverage = contract["source_coverage_requirements"]
        self.assertTrue(source_coverage["required"])
        self.assertIn("If used is true, claims_supported must be non-empty.", source_coverage["used_claims_requirement"])
        self.assertIn("If used is false, reason must be provided and claims_supported must be empty.", source_coverage["used_claims_requirement"])

        token_budget = contract["token_budget_constraints"]
        self.assertEqual(token_budget["max_context_packet_tokens"], 60000)
        self.assertEqual(token_budget["reserved_output_tokens"], 4000)
        self.assertEqual(token_budget["oversize_strategy"], "fail_or_batch")
        self.assertEqual(token_budget["truncation"], "disabled")
        self.assertTrue(token_budget["truncation_must_be_disabled"])
        self.assertTrue(token_budget["context_budget_must_be_enforced_before_call"])
        self.assertEqual(
            token_budget["oversize_strategy_behavior"],
            "fail_fast_until_batch_support_exists",
        )
        self.assertNotIn("assertions", token_budget)

        return_contract = contract["return_contract_requirements"]
        self.assertEqual(return_contract["schema_title"], "ProjectManagerReport")
        self.assertTrue(return_contract["strict"])
        self.assertTrue(return_contract["returned_object_must_validate_schema"])
        self.assertTrue(return_contract["source_coverage_required"])
        self.assertIn("source_coverage", return_contract["required_fields"])
        self.assertNotIn("required_output_type", return_contract)
        self.assertNotIn("assertions", return_contract)
        self.assertEqual(
            return_contract["schema_path"],
            str((repo_root / "harness" / "contracts" / "project_manager_report.schema.json").resolve()),
        )

    def test_model_selection_comes_from_runtime_budget_policy(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        manifest_path = repo_root / "harness" / "agents" / "project_manager.agent.json"
        role = load_role(manifest_path)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        runtime_budget = json.loads(
            (repo_root / "harness" / "policies" / "runtime_budget.policy.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertNotIn("model", manifest)
        self.assertEqual(role.model, runtime_budget["default"]["default_model"])


if __name__ == "__main__":
    unittest.main()
