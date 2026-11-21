#!/usr/bin/env bash
# Build for Ableton Move without a target glibc or toolchain sysroot.
# Freestanding DSP library: no libc, libm, dynamic linker deps, or host API copies.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build dist
python3 scripts/pack_metadata.py --check
python3 scripts/generate_metadata.py --check
python3 scripts/generate_tables.py
python3 scripts/generate_expanded_tables.py
python3 scripts/generate_noncurated_spectral.py --output build/noncurated_spectral_tables.h
python3 scripts/generate_curated_header.py --output build/curated_tables.h
CC="${CC:-clang}"
"$CC" --target=aarch64-linux-gnu -ffreestanding -nostdinc \
    -isystem "$($CC -print-resource-dir)/include" \
    -nostdlib -shared -fPIC -O2 -fvisibility=hidden \
    -DSYNTH_ESIS_ENABLE_CURATED -Ibuild \
    -fno-stack-protector -fno-builtin -fuse-ld=lld \
    -Wl,-soname,dsp.so -Wl,--no-undefined \
    src/dsp.c -o build/dsp.so
readelf -h build/dsp.so | grep -q 'AArch64'
nm -D build/dsp.so | grep -q 'move_plugin_init_v2'
if readelf -d build/dsp.so | grep -q NEEDED; then
    echo 'Unexpected dynamic dependencies' >&2;exit 1
fi
rm -rf dist/synth_esis
mkdir -p dist/synth_esis
cp build/dsp.so src/module.json src/web_ui.html src/canvas.js src/wavetable_catalog.json dist/synth_esis/
cp -R src/assets dist/synth_esis/assets
tar -C dist -czf dist/synth_esis-module.tar.gz synth_esis
printf 'Built: %s\n' "$(realpath dist/synth_esis-module.tar.gz)"
