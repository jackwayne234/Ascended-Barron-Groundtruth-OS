#!/usr/bin/env bash
# Launch the standalone desktop weather widget. (The dashboard's weather ticker
# imports weather_app.py directly; this is for running the widget on its own.)
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$APP_DIR/logs"
mkdir -p "$LOG_DIR"
cd "$APP_DIR"
exec /usr/bin/python3 "$APP_DIR/weather_app.py" >>"$LOG_DIR/launcher.out.log" 2>>"$LOG_DIR/launcher.err.log"
