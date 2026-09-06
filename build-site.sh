#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$ROOT/_site}"
mkdir -p "$OUT"
cp "$ROOT/index.html" "$OUT/index.html"
cmp "$ROOT/index.html" "$OUT/index.html"
sha256sum "$OUT/index.html"
