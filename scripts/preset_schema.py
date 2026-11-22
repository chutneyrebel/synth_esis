#!/usr/bin/env python3
"""Phase 10A: strict, versioned Synth_esis patch interchange. No hardware writes."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 1
MODULE_ID = "synth_esis"
EXCLUDED_TYPES = {"canvas", "string"}
EXCLUDED_KEYS = {"voice_activity", "face_snapshot"}

def parameter_specs():
    descriptor = json.loads((ROOT / "src/module.json").read_text())
    if descriptor["id"] != MODULE_ID:
        raise ValueError("module identity mismatch")
    return {p["key"]: p for p in descriptor["capabilities"]["chain_params"]
            if p["type"] in ("int", "float", "enum") and p["key"] not in EXCLUDED_KEYS
            and p.get("access") != "read"}

def validate_patch(patch):
    if not isinstance(patch, dict) or set(patch) != {"schema", "module_id", "name", "parameters"}:
        raise ValueError("invalid patch envelope")
    if type(patch["schema"]) is not int or patch["schema"] != SCHEMA:
        raise ValueError("unsupported patch schema")
    if patch["module_id"] != MODULE_ID:
        raise ValueError("patch belongs to another module")
    if not isinstance(patch["name"], str) or not (1 <= len(patch["name"].strip()) <= 64):
        raise ValueError("invalid patch name")
    params = patch["parameters"]
    specs = parameter_specs()
    if not isinstance(params, dict) or set(params) != set(specs):
        raise ValueError("patch parameters must match complete writable parameter set")
    for key, value in params.items():
        spec = specs[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("non-finite or non-numeric parameter: " + key)
        if spec["type"] in ("int", "enum") and (type(value) is not int):
            raise ValueError("integer parameter required: " + key)
        lo, hi = (0, len(spec["options"]) - 1) if spec["type"] == "enum" else (spec["min"], spec["max"])
        if not lo <= value <= hi:
            raise ValueError("parameter out of range: " + key)
    return patch

def migrate_legacy_patch(patch):
    """Explicit upgrade of an older valid-looking patch to the current set.

    Missing expressive controls are supported; arbitrary missing/unknown keys
    still fail strict validation. This never modifies the supplied dictionary.
    """
    if not isinstance(patch, dict):
        raise ValueError("invalid patch")
    migrated = json.loads(json.dumps(patch))
    params = migrated.get("parameters")
    if not isinstance(params, dict):
        raise ValueError("invalid patch parameters")
    specs = parameter_specs()
    missing = set(specs) - set(params)
    permitted = {"vel_spec", "vel_f", "vel_s"}
    if not missing.issubset(permitted):
        raise ValueError("missing non-migratable patch parameters")
    if set(params) - set(specs):
        raise ValueError("unknown patch parameters")
    old_amount = params.get("vel_spec", 0)
    params.setdefault("vel_spec", 0)
    params.setdefault("vel_f", old_amount)
    params.setdefault("vel_s", old_amount)
    return validate_patch(migrated)

def default_patch(name="Init"):
    return validate_patch({"schema": SCHEMA, "module_id": MODULE_ID, "name": name,
        "parameters": {key: spec.get("default", 0) for key, spec in parameter_specs().items()}})

def serialize_patch(patch):
    validate_patch(patch)
    return json.dumps(patch, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def parse_patch(data):
    if not isinstance(data, str) or len(data) > 65536:
        raise ValueError("invalid patch data size")
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate patch field: " + key)
            result[key] = value
        return result
    return validate_patch(json.loads(data, object_pairs_hook=reject_duplicates,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite number"))))

if __name__ == "__main__":
    print(serialize_patch(default_patch()))
