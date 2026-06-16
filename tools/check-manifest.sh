#!/usr/bin/env bash
# check-manifest.sh — fail if the committed MANIFEST.sha256 is stale relative to
# the current repo contents under the managed shipped-file roots.
set -euo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
A="$REPO/airootfs"
MAN="$A/usr/local/share/ai-os/MANIFEST.sha256"
TMP="$(mktemp)"
cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

(
  cd "$A"
  find usr/local/share/ai-os usr/local/lib/ai-os usr/local/bin -type f \
       ! -name INSTALLED_REV ! -name INSTALLED_VERSION ! -name MANIFEST.sha256 \
       ! -path '*/__pycache__/*' \
       \( ! -path 'usr/local/bin/*' -o -name 'ai-os-*' -o -name 'start-ai-os-*' \) \
  | LC_ALL=C sort | xargs -r sha256sum
) > "$TMP"

if cmp -s "$TMP" "$MAN"; then
  echo "MANIFEST.sha256 is current."
  exit 0
fi

echo "MANIFEST.sha256 is stale relative to the managed shipped-file set." >&2
echo "Refresh it with:" >&2
echo "  bash tools/gen-manifest.sh" >&2
echo >&2
echo "Diff against regenerated manifest:" >&2
diff -u "$MAN" "$TMP" || true
exit 1
