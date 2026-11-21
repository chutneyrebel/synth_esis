#!/usr/bin/env python3
"""Generate curated and seven compositional corner tables offline.

The Move DSP reads immutable tables and performs only interpolated lookups.
"""
import argparse
from pathlib import Path
from curated_wavetables import NAMES, FRAMES, BAND_LIMITS, N, generate_row, raw_float32_bytes
from spectral_composition import CORNER_NAMES, compose_from_base

def generate(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii") as out:
        out.write("/* Offline generated Synth_esis curated and compositional banks. */\n")
        out.write("#ifndef SYNTH_ESIS_CURATED_TABLES_H\n#define SYNTH_ESIS_CURATED_TABLES_H\n")
        out.write("#define SYNTH_ESIS_CURATED_COUNT 16\n")
        out.write("#define SYNTH_ESIS_CURATED_FRAMES 4\n")
        out.write("#define SYNTH_ESIS_CURATED_BANDS 9\n")
        out.write("#define SYNTH_ESIS_CURATED_SAMPLES 256\n")
        out.write("static const float synth_esis_curated_tables[16][4][9][256] = {\n")
        for table in range(len(NAMES)):
            out.write("{ /* " + NAMES[table] + " */\n")
            for frame in range(FRAMES):
                out.write("{\n")
                for limit in BAND_LIMITS:
                    row = generate_row(table, frame, limit)
                    out.write("{" + ",".join(format(v, ".9g") + "f" if v != 0 else "0.0f" for v in row) + "},\n")
                out.write("},\n")
            out.write("},\n")
        out.write("};\n")
        out.write("#define SYNTH_ESIS_SPECTRAL_MODES 7\n")
        out.write("static const float synth_esis_spectral_tables[7][16][4][9][256] = {\n")
        for mode, name in enumerate(CORNER_NAMES):
            out.write("{ /* " + name + " */\n")
            for table in range(len(NAMES)):
                out.write("{\n")
                for frame in range(FRAMES):
                    out.write("{\n")
                    for limit in BAND_LIMITS:
                        row = compose_from_base(generate_row(table, frame, limit), frame, limit, table, mode + 1)
                        out.write("{" + ",".join(format(v, ".9g") + "f" if v != 0 else "0.0f" for v in row) + "},\n")
                    out.write("},\n")
                out.write("},\n")
            out.write("},\n")
        out.write("};\n")
        out.write("_Static_assert(sizeof(synth_esis_spectral_tables) <= 5u * 1024u * 1024u, \"Spectral corner bank exceeds 5 MiB\");\n")
        out.write("#endif\n")
    return path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = generate(args.output)
    print(f"Generated {result}; raw float32 budget {raw_float32_bytes()} bytes")
