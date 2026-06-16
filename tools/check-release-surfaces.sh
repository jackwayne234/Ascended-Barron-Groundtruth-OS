#!/usr/bin/env bash
# check-release-surfaces.sh — lightweight sanity guard for public release-story surfaces.
set -euo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
cd "$REPO"

fail=0

say() { printf '%s\n' "$*"; }
err() { printf '%s\n' "$*" >&2; }

PUBLIC_FILES=(
  README.md
  docs/GETTING-STARTED.md
  CHANGELOG.md
  airootfs/usr/local/share/ai-os/CHANGELOG.md
)

# 1) Public and shipped changelog should stay in sync.
if ! cmp -s CHANGELOG.md airootfs/usr/local/share/ai-os/CHANGELOG.md; then
  err "Public and shipped changelog copies differ:"
  diff -u CHANGELOG.md airootfs/usr/local/share/ai-os/CHANGELOG.md || true
  fail=1
else
  say "Changelog copies are in sync."
fi

# 2) Retired high-risk phrases should not appear by accident on the main public release surfaces.
pattern='live USB|Work with AI|thumbdrive|persistent OS|open in terminal button|external-drive install path'
if rg -n "$pattern" "${PUBLIC_FILES[@]}" .github/releases >/tmp/release-surface-rg.out; then
  err "Retired wording found on public release surfaces:"
  cat /tmp/release-surface-rg.out >&2
  fail=1
else
  say "No retired wording found on checked public release surfaces."
fi
rm -f /tmp/release-surface-rg.out

if [ "$fail" -ne 0 ]; then
  err
  err "Release-surface check failed."
  err "If the wording is intentionally historical, keep it only in historical/session files — not current public release surfaces."
  exit 1
fi

say "Release surfaces check passed."
