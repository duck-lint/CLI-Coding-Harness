from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python generate_model.py <input_json> <output_py>")
        return 2

    input_json_path = Path(sys.argv[1])
    output_py_path = Path(sys.argv[2])

    if not input_json_path.exists():
        print(f"INPUT FILE NOT FOUND: {input_json_path}")
        return 2

    output_py_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "datamodel-codegen",
        "--input",
        str(input_json_path),
        "--input-file-type",
        "json",
        "--output",
        str(output_py_path),
    ]

    result = subprocess.run(command)

    if result.returncode != 0:
        print("FAIL: datamodel-codegen failed.")
        return result.returncode

    print(f"PASS: Pydantic model written to {output_py_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())