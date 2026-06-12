from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path


def utc_now_isoformat() -> str:
  return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open("rb") as file:
    for chunk in iter(lambda: file.read(8192), b""):
      digest.update(chunk)
  return digest.hexdigest()
