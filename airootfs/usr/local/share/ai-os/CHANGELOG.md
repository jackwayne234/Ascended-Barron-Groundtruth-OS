# Changelog

All notable changes to Ascended Barron: GroundTruth OS. This project uses
[semantic versioning](https://semver.org/). Releases are on the
[Releases page](../../releases).

## v1.1.1 — 2026-06-15

### Changed
- Restored a guarded **Install to disk** footer button so live-USB users have an
  obvious path to keep the OS, while preserving the installer warning and typed
  `ERASE` confirmation flow.

## v1.1.0 — 2026-06-15

A safer, clearer update system. Updates now come from published releases, and you
can see your version and undo an update.

### Added
- **Tag-based updates** — "Update OS" now installs the latest *published release*
  (a git tag) instead of the moving branch tip, so you only ever run versions the
  project actually cut.
- **Settings screen** (in Apps) with an Updates section: see your current
  version, **check for updates now**, turn the automatic update check on/off, and
  **undo the last update**.
- **"Undo last update"** — one click restores the previous version from the
  backup the updater makes (your work in `~/workspace` is never involved).
- **Version shown** in the bottom bar and Settings.
- **Update available banner** — a dismissible notice (in addition to the amber
  tile) when a newer version is published; it only comes back for a newer one.

### Changed
- The updater is sturdier: it re-execs itself from a temp copy, refuses to run
  twice at once, skips work when you're already current, **warns before
  overwriting files you changed**, removes files dropped in a new release, stages
  and verifies before applying, keeps the last 3 backups, and relaunches the
  dashboard directly (no black-screen risk).
- The update check now compares **release versions** (not branch commits); it can
  be turned off in Settings.
- The dashboard no longer surfaces **Install to disk** as a casual button; the
  installer remains available as an advanced terminal command.

## v1.0.2 — 2026-06-15

The OS can now update itself — so from this version on, you get future
improvements by pressing a button instead of reinstalling.

### Added
- **"Update OS" button** — updates the OS in place from the official repo. It
  backs up the current files first and only replaces the OS's own app files
  (the dashboard and its helpers); your projects, data, and settings in
  `~/workspace` are never touched. No reinstall, so nothing you've made is lost.
- **"Update available" indicator** — the Update OS tile turns amber when a newer
  version is published, so you know there's something to get. (The dashboard
  does one small version check to the project's GitHub on startup to know this.)

### Changed
- **Boots straight into your to-do list** (the Eisenhower matrix) instead of an
  empty welcome screen, with a one-line tip on how to start working a task. The
  welcome text still appears when you close an app or terminal.

## v1.0.1 — 2026-06-15

Dashboard polish and fixes, all gathered from real-hardware use.

### Added
- **WiFi status indicator** in the header — shows the connected network (or "No
  Wi-Fi" / "Wired"); click it to open WiFi Setup. Read-only via `nmcli`, no
  geolocation.
- **Timezone picker** — click the clock to choose your timezone from a filterable
  list (the OS ships as UTC). Fully manual; no GPS/location tracking.
- **"Build a new app" button** in *Add App* — names a project folder, creates a
  `ground-truth.md` in it, and opens a terminal to start building, then place the
  finished app in a square.
- **Chromium** now appears in the app grid out of the box (a Desktop launcher was
  missing before).
- **Weather widget bundled** — the bottom weather ticker now works instead of
  showing "Weather unavailable" (set your city in
  `~/workspace/desktop weather app/config.json`; defaults to New York, NY).
- **Tap-to-click** enabled on touchpads (a light tap clicks; no need to press the
  pad down).

### Changed
- Renamed the resource label **"Live space" → "Storage."**
- WiFi and battery indicators are now **plain text** (the emoji icons rendered as
  hollow outlines with no emoji font) and **fixed-width**, so the header no longer
  shifts as status changes.

## v1.0.0 — 2026-06-14

Initial public release.

- AI-native project workflow: create a task → **Work with AI** → project folder +
  `ground-truth.md` + a terminal in it. Bring your own AI.
- Live "try it" boot + **Install to disk** (UEFI + legacy BIOS; single-user, boots
  straight to the dashboard; no login/password).
- Local-only action logging with export-to-training-data.
- Three sample projects + a sample training-data export.
- The OS can improve itself through its own workflow.
