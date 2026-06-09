from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from pydantic import BaseModel


def load_model_class(model_file_path: Path, class_name: str) -> type[BaseModel]:
  """Load a Pydantic model class from a Python file."""

  module_name = model_file_path.stem

  module_spec = importlib.util.spec_from_file_location(
      module_name,
      model_file_path,
  )

  if module_spec is None or module_spec.loader is None:
      raise RuntimeError(f"Could not load Python file: {model_file_path}")

  module = importlib.util.module_from_spec(module_spec)

  # This is the important line.
  # It lets Pydantic resolve references like "Metadata" inside the loaded file.
  sys.modules[module_name] = module

  module_spec.loader.exec_module(module)

  model_class = getattr(module, class_name)

  if not issubclass(model_class, BaseModel):
      raise TypeError(f"{class_name} is not a Pydantic BaseModel class.")

  # This tells Pydantic:
  # "Now that the whole module is loaded, resolve any delayed type references."
  model_class.model_rebuild()

  return model_class


def main() -> int:
  """Generate a JSON Schema file from a Pydantic model class."""

  if len(sys.argv) != 4:
      print(
          "Usage: python schema_generator.py "
          "<schema_generator.py> <SchemaGenerator> <SchemaGenerator.schema.json>"
      )
      return 2

  model_file_path = Path(sys.argv[1])
  class_name = sys.argv[2]
  output_schema_path = Path(sys.argv[3])

  if not model_file_path.exists():
      print(f"MODEL FILE NOT FOUND: {model_file_path}")
      return 2

  try:
      model_class = load_model_class(model_file_path, class_name)

      schema = {
          "$schema": "https://json-schema.org/draft/2020-12/schema",
          **model_class.model_json_schema(),
      }

      output_schema_path.parent.mkdir(parents=True, exist_ok=True)

      with output_schema_path.open("w", encoding="utf-8") as file:
          json.dump(schema, file, indent=2)

  except Exception as error:
      print("FAIL: Could not generate schema.")
      print(error)
      return 1

  print(f"PASS: Schema written to {output_schema_path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())