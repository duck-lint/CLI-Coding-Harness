import sys
from pathlib import Path

# Support direct execution from harness/ while preserving package imports.
if __package__ in {None, ""}:
  sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.runtime.package_route import main


if __name__ == "__main__":
  raise SystemExit(main())
