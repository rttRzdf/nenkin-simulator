#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$ROOT/_site}"
EXPECTED_SHA256="44624826fadd73006a44facdc04e290334d369b0045006a8505476f4d4a1f930"
EXPECTED_PART01_SHA1="ceb8b5c522d97ea36f0693f729d4303457b41841"

rm -rf "$OUT"
mkdir -p "$OUT"

python3 - "$ROOT" "$OUT/part-01.repaired" "$EXPECTED_PART01_SHA1" <<'PY'
from pathlib import Path
import hashlib, sys
root = Path(sys.argv[1])
out = Path(sys.argv[2])
expected = sys.argv[3]
part = bytearray((root / "site-payload/part-01").read_bytes())
fix = (root / "site-payload/part-01-fix-09728").read_bytes()
if len(part) != 12304 or len(fix) != 512:
    raise SystemExit("payload repair length mismatch")
part[9728:10240] = fix
actual = hashlib.sha1(part).hexdigest()
if actual != expected:
    raise SystemExit(f"payload repair SHA-1 mismatch: {actual}")
out.write_bytes(part)
print(f"part-01 repaired and verified: {actual}")
PY

cat \
  "$ROOT/site-payload/part-00" \
  "$OUT/part-01.repaired" \
  "$ROOT/site-payload/part-02" \
  "$ROOT/site-payload/part-03" \
  | base64 --decode | gzip -dc > "$OUT/index.html"

rm "$OUT/part-01.repaired"
echo "$EXPECTED_SHA256  $OUT/index.html" | sha256sum -c -
echo "Built and verified $OUT/index.html"
