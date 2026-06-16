# Update 5 — Pre-release verification discipline

Purpose:
Turn the current release-readiness knowledge into a repeatable checklist or workflow that gets used before every public release.

Why this matters:
Right now the release discipline exists mostly in practice and memory. It should become a visible, repeatable release gate.

Targets to verify before release:
- README
- docs/GETTING-STARTED.md
- CHANGELOG.md
- airootfs/usr/local/share/ai-os/CHANGELOG.md
- `.github/releases/vX.Y.Z.md`
- `airootfs/usr/local/share/ai-os/MANIFEST.sha256`
- any UI/install/update wording affected by the release

Goals for a future session:
1. Create a release checklist document.
2. Decide whether it should live in `docs/`, `.github/`, or `updates/`.
3. Make it explicit which checks are mandatory before tagging.
4. Include quick commands for syntax checks, manifest refresh, and stale-term scans.
5. Distinguish between release blockers and non-blocking notes.

Suggested checklist sections:
- docs match actual UI
- release notes exist
- shipped docs updated
- manifest refreshed
- Python compile checks pass
- shell syntax checks pass
- git status clean before tagging
- release assets and SHA256SUMS verified after build

Good future outcome:
A single release-checklist document the next session can actually run through before a tag.

Recommended next-session prompt:
Open `updates/update5.md` first. Create a release-checklist document for this repo with exact checks, commands, and blocker criteria, using the current release-readiness process as ground truth.

## Progress snapshot — 2026-06-16

What was completed in this session:
1. Chose the checklist location.
   - Decision: put the checklist in `docs/RELEASE-CHECKLIST.md`
   - Reason: this is repo process and release discipline, not just workflow internals, so it should live near the other maintained docs.

2. Created the release checklist document.
   - Added `docs/RELEASE-CHECKLIST.md`
   - The checklist includes:
     - pre-tag blocker checks
     - exact commands where possible
     - blocker criteria vs non-blocking notes
     - post-build GitHub release verification
     - local checksum verification of downloaded assets
     - stronger artifact/live verification guidance for releases that change boot/install/update/dashboard behavior

3. Grounded the checklist in the repo’s real current commands and workflow.
   - Verified working commands during this pass:
     - `python3 -m py_compile airootfs/usr/local/share/ai-os/ai-os-dashboard.py airootfs/usr/local/share/ai-os/dashboard/*.py`
     - shell syntax checks for:
       - `build.sh`
       - `bootstrap-updater.sh`
       - `tools/gen-manifest.sh`
       - `airootfs/usr/local/bin/ai-os-update`
       - `airootfs/usr/local/bin/ai-os-rollback`
       - `airootfs/usr/local/bin/ai-os-install-to-disk`
   - Re-read `.github/workflows/build-release-iso.yml` so the checklist matches the actual build/release flow now in the repo.

### Current status

The main goal of this track is now satisfied:
- there is a single release-checklist document the next session can actually run before a tag
- it explicitly names release blockers
- it includes the high-value commands that were previously living mostly in practice/memory

### Optional future follow-on

1. Add lightweight automation only where it clearly pays off.
2. If future release checks grow, consider linking this checklist from the README contributor/release area or from `.github/` docs.
3. Keep this checklist aligned with any future manifest or release-workflow automation from later update tracks.