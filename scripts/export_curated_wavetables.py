#!/usr/bin/env python3
"""Export the 16 curated prototype tables to the versioned custom format.

Exports the highest-resolution band as four frames. The eventual Move runtime
must regenerate/select pitch-band-limited playback tables before audio use.
"""
import argparse
from pathlib import Path
from curated_wavetables import NAMES, FRAMES, BAND_LIMITS, generate_row
from custom_wavetable import save, load

def export(directory):
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, name in enumerate(NAMES):
        frames = [generate_row(index, frame, BAND_LIMITS[0])
                  for frame in range(FRAMES)]
        path = destination / f"curated_{index:02d}.json"
        save(path, name, frames)
        if load(path)["name"] != name:
            raise ValueError("export verification failed")
        paths.append(path)
    return paths

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    for path in export(args.output_dir):
        print(path)
