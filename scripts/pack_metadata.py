#!/usr/bin/env python3
"""Generate the loader-size-limited Schwung descriptor from richer source JSON.

Only duplicate FACE page declaration is compacted. Parameter keys, names,
ranges, defaults and IDs must remain byte-for-byte equivalent semantically.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/module.source.json"
TARGET = ROOT / "src/module.json"
MAX_BYTES = 8192


def pack():
    data = json.loads(SOURCE.read_text())
    packed = json.loads(json.dumps(data))
    caps = packed["capabilities"]
    root = caps["ui_hierarchy"]["levels"]["root"]
    expected = {"key": "face", "type": "canvas", "as_page": True, "page_first": True}
    if root["params"][0] != expected:
        raise ValueError("FACE structure changed: compaction requires review")
    face = next(p for p in caps["chain_params"] if p["key"] == "face")
    if face.get("as_page") is not True or face.get("page_first") is not True:
        raise ValueError("FACE flags must remain in chain_params")
    root["params"][0] = "face"
    # Strictly verify that ONLY the duplicated structural FACE reference was
    # changed. This forbids silent parameter/default/label modifications.
    roundtrip = json.loads(json.dumps(packed))
    roundtrip["capabilities"]["ui_hierarchy"]["levels"]["root"]["params"][0] = expected
    if roundtrip != data:
        raise ValueError("compaction changed unrelated metadata")
    output = json.dumps(packed, separators=(",", ":"), ensure_ascii=True) + "\n"
    if len(output.encode()) >= MAX_BYTES:
        raise ValueError("Schwung descriptor >=8192 bytes: redesign needed")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = pack()
    if args.check:
        if not TARGET.exists() or TARGET.read_text() != output:
            raise SystemExit("module.json out of sync; run python3 scripts/pack_metadata.py")
        print("PASS: compact Schwung descriptor and canonical source in sync")
    else:
        TARGET.write_text(output)
        print("Generated", TARGET.relative_to(ROOT), len(output.encode()), "bytes")
