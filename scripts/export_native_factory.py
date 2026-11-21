#!/usr/bin/env python3
"""Export factory recipes to Schwung's native per-module preset JSON format.

Offline only. Does not access or write to Ableton Move.
Uses the actual compiled DSP to produce canonical :state strings.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import subprocess
import tempfile

from preset_schema import migrate_legacy_patch

ROOT = Path(__file__).resolve().parents[1]
CREATE = C.CFUNCTYPE(C.c_void_p, C.c_char_p, C.c_char_p)
DESTROY = C.CFUNCTYPE(None, C.c_void_p)
MIDI = C.CFUNCTYPE(None, C.c_void_p, C.POINTER(C.c_uint8), C.c_int, C.c_int)
SET = C.CFUNCTYPE(None, C.c_void_p, C.c_char_p, C.c_char_p)
GET = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_char_p, C.c_char_p, C.c_int)
RENDER = C.CFUNCTYPE(None, C.c_void_p, C.POINTER(C.c_int16), C.c_int)

class Plugin(C.Structure):
    _fields_ = [("api_version", C.c_uint32), ("create", CREATE),
                ("destroy", DESTROY), ("midi", MIDI), ("set", SET),
                ("get", GET), ("error", GET), ("render", RENDER)]

def export_factory(output_dir):
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("output directory must be empty")
    catalog = json.loads((ROOT / "presets/factory.json").read_text())
    if catalog.get("schema") != 1 or len(catalog.get("presets", [])) != 16:
        raise ValueError("unexpected factory catalog")
    entries = []
    for item in catalog["presets"]:
        upgraded = migrate_legacy_patch(item["patch"])
        entries.append({**item, "patch": upgraded})
    names = [x["patch"]["name"] for x in entries]
    if len(set(names)) != len(names):
        raise ValueError("duplicate factory names")

    with tempfile.TemporaryDirectory() as temp:
        so = Path(temp) / "dsp.so"
        subprocess.run(["python3", str(ROOT / "scripts/generate_metadata.py"), "--check"], check=True)
        subprocess.run(["python3", str(ROOT / "scripts/generate_tables.py")], check=True)
        subprocess.run(["python3", str(ROOT / "scripts/generate_expanded_tables.py")], check=True)
        subprocess.run(["gcc", "-std=c11", "-O2", "-shared", "-fPIC", "-ffreestanding",
                        "-fno-builtin", "-fvisibility=hidden", str(ROOT / "src/dsp.c"),
                        "-o", str(so)], check=True)
        lib = C.CDLL(str(so))
        lib.move_plugin_init_v2.restype = C.POINTER(Plugin)
        lib.move_plugin_init_v2.argtypes = [C.c_void_p]
        api = lib.move_plugin_init_v2(None).contents
        if api.api_version != 2:
            raise ValueError("unsupported plugin ABI")
        documents = []
        for item in entries:
            instance = api.create(b".", None)
            if not instance:
                raise RuntimeError("DSP instance unavailable")
            try:
                for key, value in item["patch"]["parameters"].items():
                    api.set(instance, key.encode(), str(value).encode())
                buf = C.create_string_buffer(8192)
                if api.get(instance, b"state", buf, len(buf)) <= 0:
                    raise RuntimeError("native state read failed")
                state = buf.value.decode("ascii")
                if len(state) >= 2048:
                    raise ValueError("native state exceeds DSP parser bound")
                # Verify the actual exported string can be loaded by a new
                # DSP instance before making a downloadable preset file.
                restored = api.create(b".", None)
                if not restored:
                    raise RuntimeError("restore instance unavailable")
                try:
                    api.set(restored, b"state", state.encode("ascii"))
                    check = C.create_string_buffer(8192)
                    if api.get(restored, b"state", check, len(check)) <= 0:
                        raise RuntimeError("native state restore read failed")
                    if check.value.decode("ascii") != state:
                        raise ValueError("factory preset lost parameters on native restore: " + item["id"])
                finally:
                    api.destroy(restored)
            finally:
                api.destroy(instance)
            documents.append({"name": item["patch"]["name"], "module": "synth_esis",
                              "version": 1, "state": state})

    output_dir.mkdir(parents=True, exist_ok=True)
    for idx, doc in enumerate(documents, 1):
        filename = f"Factory {idx:02d} - {doc['name']}.json"
        (output_dir / filename).write_text(json.dumps(doc, ensure_ascii=True, indent=2) + "\n")
    return len(documents)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(f"Exported {export_factory(args.output_dir)} native factory presets to {args.output_dir}")
