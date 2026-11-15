#!/usr/bin/env python3
"""Check that approved web appearance files remain byte-identical to source."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "snapshot/SOURCE-LOCK.json").read_text(encoding="utf-8"))

for relative, expected in LOCK["protectedWebFiles"].items():
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"MISSING protected reference file: {relative}")
    content = path.read_bytes()
    header = b"blob " + str(len(content)).encode("ascii") + bytes([0])
    actual = hashlib.sha1(header + content).hexdigest()
    if actual != expected:
        raise SystemExit(f"REFERENCE CHANGED: {relative} expected={expected} actual={actual}")

print(f"PASS: {len(LOCK['protectedWebFiles'])} approved web appearance files are unchanged.")
