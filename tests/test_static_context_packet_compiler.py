from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from harness.project_spec.static_context_packet import StaticContextPacket
from harness.project_spec.static_context_packet_compiler import (
  StaticContextCompilationError,
  compile_static_context_packet,
  enforce_cardinality,
  enforce_no_undeclared_included_sources,
  load_and_validate_manifest,
)
from harness.project_spec.static_context_packet_manifest import Source


REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = REPO_ROOT / "harness"
MANIFEST_PATH = HARNESS_ROOT / "project_spec" / "static_context_packet.manifest.json"
PACKET_SCHEMA_PATH = HARNESS_ROOT / "project_spec" / "StaticContextPacket.schema.json"


def copy_target_sources(
  destination: Path,
  *,
  include_known_failures: bool = True,
  include_active_implementation: bool = False,
) -> Path:
  target_root = destination / "target"
  project_spec_root = target_root / "project_spec"
  project_spec_root.mkdir(parents=True)

  source_names = ["project_spec.json", "open_decisions.json"]
  if include_known_failures:
    source_names.append("known_failures.json")

  for source_name in source_names:
    shutil.copy2(
      HARNESS_ROOT / "project_spec" / source_name,
      project_spec_root / source_name,
    )

  if include_active_implementation:
    active_root = target_root / "implementations" / "active"
    active_root.mkdir(parents=True)
    shutil.copy2(
      HARNESS_ROOT / "implementations" / "active" / "implementation_plan_01.json",
      active_root / "implementation_plan_01.json",
    )
    shutil.copy2(
      HARNESS_ROOT / "implementations" / "active" / "implementation_tracker_01.json",
      active_root / "implementation_tracker_01.json",
    )

  return target_root


class StaticContextPacketCompilerTests(unittest.TestCase):
  def test_current_manifest_validates(self) -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)

    self.assertEqual(len(manifest.sources), 6)
    self.assertEqual(
      {source.source_id for source in manifest.sources},
      {
        "governance_primitives",
        "project_spec",
        "known_failures",
        "open_decisions",
        "active_implementation_plan",
        "active_implementation_tracker",
      },
    )

  def test_compiler_emits_valid_packet_with_all_live_sources(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      output_path = Path(temp_directory) / "static_context_packet.json"

      packet = compile_static_context_packet(
        MANIFEST_PATH,
        HARNESS_ROOT,
        HARNESS_ROOT,
        output_path,
      )

      self.assertTrue(output_path.is_file())
      self.assertEqual(len(packet.source_coverage), 6)
      self.assertTrue(
        all(entry.status == "included" for entry in packet.source_coverage)
      )
      self.assertTrue(
        all(
          entry.validation.status == "passed"
          and entry.validation.validator == "pydantic"
          and entry.validation.model == entry.schema_id
          and entry.validation.normalized_output_available
          for entry in packet.source_coverage
        )
      )
      self.assertEqual(packet.missing_sources, [])
      self.assertEqual(
        packet.governance_primitives["metadata"]["document_id"],
        "governance_primitives.json",
      )
      self.assertEqual(
        packet.project_spec["metadata"]["document_id"],
        "project_spec.json",
      )
      self.assertEqual(
        packet.known_failures["metadata"]["document_id"],
        "known_failures.json",
      )
      self.assertEqual(
        packet.open_decisions["metadata"]["document_id"],
        "open_decisions.json",
      )
      self.assertIsNotNone(packet.active_implementation_plan)
      self.assertIsNotNone(packet.active_implementation_tracker)

      emitted = json.loads(output_path.read_text(encoding="utf-8"))
      self.assertEqual(StaticContextPacket.model_validate(emitted), packet)

  def test_optional_active_sources_are_recorded_absent(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      target_root = copy_target_sources(temp_root)
      output_path = temp_root / "static_context_packet.json"

      packet = compile_static_context_packet(
        MANIFEST_PATH,
        HARNESS_ROOT,
        target_root,
        output_path,
      )

      self.assertIsNone(packet.active_implementation_plan)
      self.assertIsNone(packet.active_implementation_tracker)
      self.assertEqual(
        {entry.source_id for entry in packet.missing_sources},
        {
          "active_implementation_plan",
          "active_implementation_tracker",
        },
      )
      self.assertTrue(
        all(
          entry.effect == "recorded_absent"
          for entry in packet.missing_sources
        )
      )
      self.assertEqual(
        {
          entry.source_id
          for entry in packet.source_coverage
          if entry.status == "missing"
        },
        {
          "active_implementation_plan",
          "active_implementation_tracker",
        },
      )
      self.assertTrue(
        all(
          entry.validation.status == "not_run"
          and not entry.validation.normalized_output_available
          for entry in packet.source_coverage
          if entry.status == "missing"
        )
      )

  def test_invalid_optional_source_blocks_compilation(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      target_root = copy_target_sources(
        temp_root,
        include_active_implementation=True,
      )
      plan_path = (
        target_root
        / "implementations"
        / "active"
        / "implementation_plan_01.json"
      )
      raw = json.loads(plan_path.read_text(encoding="utf-8"))
      raw["unvalidated_extra"] = True
      plan_path.write_text(json.dumps(raw), encoding="utf-8")
      output_path = temp_root / "static_context_packet.json"

      with self.assertRaises(StaticContextCompilationError) as error:
        compile_static_context_packet(
          MANIFEST_PATH,
          HARNESS_ROOT,
          target_root,
          output_path,
        )

      self.assertFalse(output_path.exists())
      self.assertTrue(
        any(
          entry.source_id == "active_implementation_plan"
          and entry.status == "invalid"
          and entry.validation.status == "failed"
          and not entry.validation.normalized_output_available
          for entry in error.exception.source_coverage
        )
      )

  def test_missing_required_source_blocks_without_emitting_packet(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      target_root = copy_target_sources(
        temp_root,
        include_known_failures=False,
      )
      output_path = temp_root / "static_context_packet.json"

      with self.assertRaises(StaticContextCompilationError) as error:
        compile_static_context_packet(
          MANIFEST_PATH,
          HARNESS_ROOT,
          target_root,
          output_path,
        )

      self.assertFalse(output_path.exists())
      self.assertTrue(
        any(
          entry.source_id == "known_failures"
          and entry.effect == "blocks_compilation"
          for entry in error.exception.missing_sources
        )
      )

  def test_invalid_required_source_blocks_without_raw_dict_inclusion(
    self,
  ) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)
      target_root = copy_target_sources(temp_root)
      known_failures_path = target_root / "project_spec" / "known_failures.json"
      raw = json.loads(known_failures_path.read_text(encoding="utf-8"))
      raw["unvalidated_extra"] = True
      known_failures_path.write_text(json.dumps(raw), encoding="utf-8")
      output_path = temp_root / "static_context_packet.json"

      with self.assertRaises(StaticContextCompilationError) as error:
        compile_static_context_packet(
          MANIFEST_PATH,
          HARNESS_ROOT,
          target_root,
          output_path,
        )

      self.assertFalse(output_path.exists())
      self.assertTrue(
        any(
          entry.source_id == "known_failures"
          and entry.status == "invalid"
          and entry.validation.status == "failed"
          for entry in error.exception.source_coverage
        )
      )

  def test_undeclared_packet_source_is_invalid(self) -> None:
    manifest = load_and_validate_manifest(MANIFEST_PATH)

    with self.assertRaises(StaticContextCompilationError) as error:
      enforce_no_undeclared_included_sources(
        {
          "governance_primitives": {},
          "unexpected_runtime_document": {},
        },
        manifest,
        source_coverage=[],
        missing_sources=[],
      )

    self.assertIn("unexpected_runtime_document", str(error.exception))

  def test_emitted_packet_validates_against_generated_schema(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      output_path = Path(temp_directory) / "static_context_packet.json"
      compile_static_context_packet(
        MANIFEST_PATH,
        HARNESS_ROOT,
        HARNESS_ROOT,
        output_path,
      )

      schema = json.loads(PACKET_SCHEMA_PATH.read_text(encoding="utf-8"))
      emitted = json.loads(output_path.read_text(encoding="utf-8"))

      Draft202012Validator.check_schema(schema)
      Draft202012Validator(schema).validate(emitted)

  def test_generated_schema_has_no_invalid_sources_category(self) -> None:
    schema = json.loads(PACKET_SCHEMA_PATH.read_text(encoding="utf-8"))

    self.assertNotIn("InvalidSourceEntry", schema.get("$defs", {}))
    self.assertNotIn("invalid_sources", schema["properties"])

  def test_all_cardinality_modes(self) -> None:
    cases = [
      ("exactly_one", 1, True),
      ("exactly_one", 0, False),
      ("zero_or_one", 0, True),
      ("zero_or_one", 2, False),
      ("zero_or_more", 0, True),
      ("zero_or_more", 2, True),
      ("one_or_more", 1, True),
      ("one_or_more", 0, False),
    ]

    with tempfile.TemporaryDirectory() as temp_directory:
      temp_root = Path(temp_directory)

      for cardinality, count, is_valid in cases:
        with self.subTest(cardinality=cardinality, count=count):
          source = Source.model_construct(
            source_id="project_spec",
            cardinality=cardinality,
          )
          paths = [temp_root / f"{index}.json" for index in range(count)]

          if is_valid:
            enforce_cardinality(source, paths)
          else:
            with self.assertRaises(ValueError):
              enforce_cardinality(source, paths)

  def test_compiler_supports_direct_script_execution(self) -> None:
    with tempfile.TemporaryDirectory() as temp_directory:
      output_path = Path(temp_directory) / "static_context_packet.json"
      script_path = (
        HARNESS_ROOT / "project_spec" / "static_context_packet_compiler.py"
      )

      completed = subprocess.run(
        [
          sys.executable,
          str(script_path),
          "--output",
          str(output_path),
        ],
        cwd=script_path.parent,
        capture_output=True,
        text=True,
        check=False,
      )

      self.assertEqual(completed.returncode, 0, completed.stderr)
      self.assertTrue(output_path.is_file())
      self.assertIn("PASS: Static context packet written", completed.stdout)


if __name__ == "__main__":
  unittest.main()
