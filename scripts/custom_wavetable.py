#!/usr/bin/env python3
"""Offline custom wavetable interchange v1; not a Move runtime loader."""
import json
import math
from pathlib import Path

VERSION = 1
FRAME_COUNT = 4
SAMPLE_COUNT = 256
MAX_BYTES = 100_000
MAX_NAME = 48

def validate(payload):
    if not isinstance(payload, dict) or set(payload) != {"format", "version", "name", "frames"}:
        raise ValueError("unexpected wavetable schema")
    if payload["format"] != "synth_esis.wavetable" or type(payload["version"]) is not int or payload["version"] != VERSION:
        raise ValueError("unsupported wavetable version")
    name = payload["name"]
    if not isinstance(name, str) or not 1 <= len(name) <= MAX_NAME or any(ord(c) < 32 for c in name):
        raise ValueError("invalid name")
    frames = payload["frames"]
    if not isinstance(frames, list) or len(frames) != FRAME_COUNT:
        raise ValueError("expected four frames")
    for frame in frames:
        if not isinstance(frame, list) or len(frame) != SAMPLE_COUNT:
            raise ValueError("expected 256 samples per frame")
        for value in frame:
            if type(value) not in (float, int) or not math.isfinite(value) or abs(value) > 1:
                raise ValueError("samples must be finite and in [-1, 1]")
    return payload

def encode(name, frames):
    payload = {"format": "synth_esis.wavetable", "version": VERSION,
               "name": name, "frames": frames}
    validate(payload)
    result = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    if len(result.encode("utf-8")) > MAX_BYTES:
        raise ValueError("wavetable exceeds size limit")
    return result

def decode(raw):
    if isinstance(raw, bytes):
        if len(raw) > MAX_BYTES:
            raise ValueError("wavetable exceeds size limit")
        raw = raw.decode("utf-8")
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_BYTES:
        raise ValueError("wavetable exceeds size limit")
    def no_duplicates(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("duplicate field")
            obj[key] = value
        return obj
    return validate(json.loads(raw, object_pairs_hook=no_duplicates,
                               parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite JSON"))))

def save(path, name, frames):
    Path(path).write_text(encode(name, frames), encoding="utf-8")

def load(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("wavetable exceeds size limit")
    return decode(path.read_bytes())
