#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$ROOT/_site}"
EXPECTED_SHA256="44624826fadd73006a44facdc04e290334d369b0045006a8505476f4d4a1f930"

python3 - "$ROOT/site-payload/part-01" <<'PY'
from pathlib import Path
import hashlib, sys
p = Path(sys.argv[1]).read_bytes()
print(f"part-01 length={len(p)} sha1={hashlib.sha1(p).hexdigest()}")
for i in range(0, len(p), 512):
    print(f"part-01 block {i:05d} {hashlib.sha1(p[i:i+512]).hexdigest()}")
PY

rm -rf "$OUT"
mkdir -p "$OUT"
cat "$ROOT"/site-payload/part-* | base64 --decode | gzip -dc > "$OUT/index.html"
echo "$EXPECTED_SHA256  $OUT/index.html" | sha256sum -c -

echo "Built $OUT/index.html"
