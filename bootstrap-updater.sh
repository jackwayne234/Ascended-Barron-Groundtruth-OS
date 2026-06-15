#!/usr/bin/env bash
# bootstrap-updater.sh — one-time helper for OLD installs (v1.0.0 / v1.0.1) that
# predate the in-place updater. It installs the updater, then runs it once. After
# this, the "Update OS" button takes over and you never need this again. (Q22)
#
# Usage (on the old install):
#   curl -fsSL https://raw.githubusercontent.com/jackwayne234/Ascended-Barron-Groundtruth-OS/main/bootstrap-updater.sh | bash
#
# Prefer not to pipe to bash? The exact steps are below — run them by hand.
set -euo pipefail

REPO_URL="https://github.com/jackwayne234/Ascended-Barron-Groundtruth-OS.git"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Ascended Barron: GroundTruth OS — one-time updater bootstrap"
echo "==========================================================="
command -v git >/dev/null 2>&1 || { echo "git is required."; exit 1; }

echo "Downloading the latest app code..."
git clone --depth 1 "$REPO_URL" "$TMP/repo" -q

SRC="$TMP/repo/airootfs"
echo "Installing the updater..."
sudo install -m755 "$SRC/usr/local/bin/ai-os-update"    /usr/local/bin/
sudo install -m755 "$SRC/usr/local/bin/ai-os-rollback"  /usr/local/bin/ 2>/dev/null || true
sudo install -d /usr/local/share/ai-os

echo
echo "✓ Updater installed. Running it now to pull the latest release..."
echo
exec ai-os-update
