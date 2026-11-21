#!/usr/bin/env python3
"""Offline full-depth spectral composition bank for the 108 original WT IDs.

Seven compositional corners per table/frame/pitch band, stored as signed int16
to cap immutable ROM footprint. No new runtime FFT, allocation, or threading.
All values come from generated historical tables; the original tables remain
untouched and zero-depth lookup bypasses this bank bit-for-bit.
"""
import argparse
from pathlib import Path
import re
from spectral_composition import compose_from_base

ROOT = Path(__file__).resolve().parents[1]
WAVES, FRAMES, BANDS, SAMPLES, CORNERS = 108, 4, 9, 256, 7
BAND_LIMITS = (96, 64, 48, 32, 24, 16, 8, 4, 1)
BYTES = CORNERS * WAVES * FRAMES * BANDS * SAMPLES * 2


def _read_rows(filename, marker, count):
    source = filename.read_text()
    pos = source.find(marker)
    if pos < 0:
        raise ValueError("missing generated table marker: " + marker)
    start = source.index("{", pos)
    stop = source.index("};", start)
    rows = re.findall(r"\{([^{}]+)\}", source[start:stop])
    if len(rows) != count:
        raise ValueError(f"expected {count} table rows in {filename}, saw {len(rows)}")
    for row in rows:
        values = [float(v[:-1]) if v.endswith("f") else float(v)
                  for v in row.split(",") if v.strip()]
        if len(values) != SAMPLES:
            raise ValueError("incorrect generated row length")
        yield values


def generated_source_rows():
    """Yield (table_id, frame, band_idx, waveform) for original IDs 0..107."""
    arrays = (
        _read_rows(ROOT / "src/tables.h", "sprig_wavetables[4][4][9][256]", 4 * FRAMES * BANDS),
        _read_rows(ROOT / "src/expanded_tables.h",
                   "sprig_expanded_tables[104][4][9][256]", 104 * FRAMES * BANDS)
    )
    for table, rows in enumerate(arrays):
        wave_start = 0 if table == 0 else 4
        for row_index, base in enumerate(rows):
            source_id = wave_start + row_index // (FRAMES * BANDS)
            frame = row_index // BANDS % FRAMES
            band = row_index % BANDS
            yield source_id, frame, band, base


def generate(output):
    """Build a bounded, immutable, fully compositional int16 C bank."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Cache 108 x 4 x 9 source rows once; generation is offline, not RT.
    rows = [[[[0.0] * SAMPLES for _ in range(BANDS)]
             for _ in range(FRAMES)] for _ in range(WAVES)]
    for wave, frame, band, data in generated_source_rows():
        rows[wave][frame][band] = data
    with output.open("w", encoding="ascii") as out:
        out.write("/* Generated offline; seven spectral composition corners for 108 existing WT IDs. */\n")
        out.write("#ifndef SYNTH_ESIS_NONCURATED_SPECTRAL_H\n#define SYNTH_ESIS_NONCURATED_SPECTRAL_H\n")
        out.write("#define SYNTH_ESIS_NONCURATED_SPECTRAL_COUNT 108\n")
        out.write("#define SYNTH_ESIS_NONCURATED_SPECTRAL_CORNERS 7\n")
        out.write("static const int16_t synth_esis_noncurated_spectral_tables[7][108][4][9][256] = {\n")
        for mask in range(1, CORNERS + 1):
            out.write("{ /* composition mask " + str(mask) + " */\n")
            for source_id in range(WAVES):
                out.write("{\n")
                for frame in range(FRAMES):
                    out.write("{\n")
                    for band, limit in enumerate(BAND_LIMITS):
                        transformed = compose_from_base(rows[source_id][frame][band],
                                                        frame, limit, source_id, mask)
                        quantized = [max(-32768, min(32767, int(round(x * 32767))))
                                     for x in transformed]
                        out.write("{" + ",".join(str(x) for x in quantized) + "},\n")
                    out.write("},\n")
                out.write("},\n")
            out.write("},\n")
        out.write("};\n")
        out.write("_Static_assert(sizeof(synth_esis_noncurated_spectral_tables)"
                  " <= 14u * 1024u * 1024u, \"Noncurated spectral bank exceeds 14 MiB\");\n")
        out.write("#endif\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print("Generated", generate(args.output), "noncurated composition raw bytes", BYTES)
