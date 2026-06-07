from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError, SchemaError


def load_json(path: Path) -> dict:
  """Read a JSON file and return its contents as Python data."""
  with path.open("r", encoding="utf-8") as file:
      return json.load(file)


def main() -> int:
  """Validate one JSON data file against one JSON schema file."""

  if len(sys.argv) != 3:
      print("Usage: python validate_data.py <data_json_path> <schema_json_path>")
      return 2

  data_path = Path(sys.argv[1])
  schema_path = Path(sys.argv[2])

  if not data_path.exists():
      print(f"DATA FILE NOT FOUND: {data_path}")
      return 2

  if not schema_path.exists():
      print(f"SCHEMA FILE NOT FOUND: {schema_path}")
      return 2

  try:
      data = load_json(data_path)
      schema = load_json(schema_path)

      Draft202012Validator.check_schema(schema)

      validator = Draft202012Validator(schema)
      validator.validate(data)

  except json.JSONDecodeError as error:
      print("FAIL: One of the files is not valid JSON.")
      print(error)
      return 1

  except SchemaError as error:
      print("FAIL: The schema file is not a valid JSON Schema.")
      print(error.message)
      return 1

  except ValidationError as error:
      print("FAIL: Data does not validate against schema.")
      print(error.message)
      return 1

  print(f"PASS: {data_path} validates against {schema_path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())