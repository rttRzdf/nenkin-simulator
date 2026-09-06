#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$ROOT/_site}"
EXPECTED_SHA256="44624826fadd73006a44facdc04e290334d369b0045006a8505476f4d4a1f930"

rm -rf "$OUT"
mkdir -p "$OUT"
cat "$ROOT"/site-payload/part-* | base64 --decode | gzip -dc > "$OUT/index.html"
echo "$EXPECTED_SHA256  $OUT/index.html" | sha256sum -c -

echo "Built $OUT/index.html"
