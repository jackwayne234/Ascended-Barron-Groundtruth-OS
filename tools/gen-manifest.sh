#!/usr/bin/env bash
# gen-manifest.sh — (re)generate the committed manifest of OS-managed app files
# (paths + SHA256). This file ships in the OS and is what ai-os-update pulls to
# detect locally-modified files (Q12/Q40) and remove files dropped in a release
# (Q2). Run it whenever a managed file under usr/local changes, and commit the
# result. make-release runs it and refuses to release if it isn't committed.
set -euo pipefail
REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
A="$REPO/airootfs"
MAN="$A/usr/local/share/ai-os/MANIFEST.sha256"

# One find (multiple roots) for shell robustness. Under usr/local/bin only the
# OS's own launchers count (ai-os-* and start-ai-os-*); elsewhere all files do.
# Excludes the generated version markers, the manifest itself, and bytecode.
( cd "$A" && \
  find usr/local/share/ai-os usr/local/lib/ai-os usr/local/bin -type f \
       ! -name INSTALLED_REV ! -name INSTALLED_VERSION ! -name MANIFEST.sha256 \
       ! -path '*/__pycache__/*' \
       \( ! -path 'usr/local/bin/*' -o -name 'ai-os-*' -o -name 'start-ai-os-*' \) \
  | LC_ALL=C sort | xargs -r sha256sum ) > "$MAN"
echo "wrote $MAN ($(wc -l < "$MAN") managed files)"
