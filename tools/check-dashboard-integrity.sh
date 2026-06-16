#!/usr/bin/env bash
# check-dashboard-integrity.sh — module-aware dashboard guard after modularization.
set -euo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
cd "$REPO"

DASH_ROOT="airootfs/usr/local/share/ai-os"
DASH_ENTRY="$DASH_ROOT/ai-os-dashboard.py"
DASH_MODULE_DIR="$DASH_ROOT/dashboard"
SMOKE_SCRIPT="qa/dashboard_smoke.py"

if [ ! -f "$DASH_ENTRY" ]; then
  echo "Missing dashboard entrypoint: $DASH_ENTRY" >&2
  exit 1
fi

if [ ! -d "$DASH_MODULE_DIR" ]; then
  echo "Missing dashboard module directory: $DASH_MODULE_DIR" >&2
  exit 1
fi

mapfile -t module_files < <(find "$DASH_MODULE_DIR" -maxdepth 1 -type f -name '*.py' | sort)
if [ "${#module_files[@]}" -eq 0 ]; then
  echo "No dashboard module files found under $DASH_MODULE_DIR" >&2
  exit 1
fi

echo "Dashboard entrypoint present: $DASH_ENTRY"
echo "Dashboard module count: ${#module_files[@]}"

echo "Running Python compile check across launcher + dashboard modules..."
python3 -m py_compile "$DASH_ENTRY" "${module_files[@]}"

echo "Running dashboard smoke harness under Xvfb..."
if ! command -v xvfb-run >/dev/null 2>&1; then
  echo "xvfb-run is required for dashboard smoke QA but is not installed." >&2
  exit 1
fi
xvfb-run -a python3 "$SMOKE_SCRIPT"

echo "Dashboard integrity check passed."
