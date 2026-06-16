# Changelog

All notable changes to Ascended Barron: GroundTruth OS.

This project uses [semantic versioning](https://semver.org/). Releases are published on the [Releases page](../../releases).

## v1.1.3 — 2026-06-16

### Fixed
- Restored `Open Project Terminal` after the dashboard modularization split so selecting a task opens a visible terminal window again.
- Improved the live dashboard background/window behavior by removing the forced fullscreen window-manager state and reducing dependence on `xdotool`.

### Changed
- The footer resource label now shows free storage in gigabytes instead of only a storage percentage.
- Added a module-aware dashboard integrity guard and CI workflow so launcher, dashboard modules, and smoke QA are verified together.
- Added internal dashboard-structure and release-process docs for the post-modularization layout.

## v1.1.2 — 2026-06-15

### Changed
- Removed the dashboard footer button for the external-drive setup path.
- Kept the advanced terminal installer available as `sudo ai-os-install-to-disk`.
- Updated the public docs so the README, Getting Started guide, and release notes match the current UI and removable-media workflow.

## v1.1.1 — 2026-06-15

### Changed
- Restored the guarded dashboard install button for the external-drive setup path.
- Kept the safety checks in the installer, including explicit target confirmation before writing to disk.
- Updated the docs so they matched the dashboard again.

## v1.1.0 — 2026-06-15

A safer and clearer update system.

### Added
- Tag-based updates. Update OS now installs the latest published release instead of the moving branch tip.
- A Settings screen with update controls, including version display, check-now, update-check toggle, and undo.
- Undo for the last update.
- Current version display in the dashboard.
- A dismissible update-available banner in addition to the amber tile state.

### Changed
- Hardened the updater so it stages and verifies changes, warns before overwriting modified files, removes dropped files from new releases, keeps recent backups, and relaunches the dashboard directly after updating.
- Changed update checks to compare release versions instead of branch commits.
- Reframed the install path as an external-drive setup and left it available as an advanced terminal command instead of a casual dashboard action.

## v1.0.2 — 2026-06-15

GroundTruth OS can now update itself in place.

### Added
- Update OS in the dashboard.
- An update-available indicator when a newer version is published.

### Changed
- The dashboard now opens to the Eisenhower task view instead of an empty welcome screen.

## v1.0.1 — 2026-06-15

Dashboard polish and hardware-driven fixes.

### Added
- Wi-Fi status in the header, with a shortcut into Wi-Fi setup.
- A manual timezone picker from the clock.
- A Build a new app flow that creates a project folder and `ground-truth.md`, then opens a terminal there.
- Chromium in the app grid by default.
- The bundled weather widget.
- Tap-to-click support on touchpads.

### Changed
- Renamed the resource label from Live space to Storage.
- Switched Wi-Fi and battery indicators to plain text so the header stays stable on systems without emoji fonts.

## v1.0.0 — 2026-06-14

Initial public release.

### Added
- The AI-native project workflow: create a task, open its project terminal, get a `ground-truth.md`, and bring your own AI.
- Live boot from removable media with support for UEFI and legacy BIOS.
- Local workflow logging and training-data export helpers.
- Sample projects and a sample training-data export.
- The self-modification workflow for improving the OS from inside itself.
