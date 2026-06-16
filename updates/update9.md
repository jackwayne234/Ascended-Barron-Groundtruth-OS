# Update 9 — Optional future release automation improvements

Purpose:
Identify small, high-value automations that make releases safer without overengineering the repo.

Why this matters:
Some of the release hygiene in this project is repetitive and easy to forget, but not everything needs heavy CI logic.

Good automation candidates:
- fail release workflow if `.github/releases/vX.Y.Z.md` is missing for a tag
- optional stale-manifest detection
- optional doc/wording sanity checks for known high-risk phrases
- optional check that shipped changelog and public changelog both changed when release wording changes

Goals for a future session:
1. List possible automation checks.
2. Rank them by value vs complexity.
3. Pick only the smallest useful ones.
4. Implement one or two if clearly worthwhile.

Rule for this work:
- prefer small guards over complex release frameworks
- avoid adding automation that is noisy, fragile, or hard to trust

Best likely first automation:
- require a matching `.github/releases/<tag>.md` file on tagged builds

Recommended next-session prompt:
Open `updates/update9.md` first. Review possible release-safety automations for this repo, rank them by value and complexity, and implement only the smallest high-confidence guard if it is clearly worth it.

## Progress snapshot — 2026-06-16

What was completed in this session:

1. Ranked the main small automation candidates by value vs complexity.

High value / already done elsewhere:
- require matching `.github/releases/vX.Y.Z.md` on tagged builds
  - status: already implemented in the release workflow during the update3 pass
- stale-manifest detection
  - status: already implemented during the update6 pass with:
    - `tools/check-manifest.sh`
    - `.github/workflows/check-manifest.yml`

High value / still worth adding now:
- lightweight release-surface sanity check
  - scope:
    - catch retired high-risk phrases on the current public release surfaces
    - catch drift between public and shipped changelog copies
  - value: high
  - complexity: low
  - decision: implemented in this session

Lower priority / not implemented now:
- infer whether both changelog copies "should" have changed based on semantic diff heuristics
  - value: moderate
  - complexity: higher and easier to make noisy
- broader doc/story lint across many historical files
  - value: moderate
  - complexity: higher and more likely to create false positives

2. Implemented the chosen small guard.
   - New local checker script:
     - `tools/check-release-surfaces.sh`
   - The checker currently does two things:
     1. verifies `CHANGELOG.md` and `airootfs/usr/local/share/ai-os/CHANGELOG.md` stay in sync
     2. scans the main public release-story surfaces for retired high-risk phrases:
        - `live USB`
        - `Work with AI`
        - `thumbdrive`
        - `persistent OS`
        - `open in terminal button`
        - `external-drive install path`

3. Added a lightweight CI workflow for the new guard.
   - New workflow:
     - `.github/workflows/check-release-surfaces.yml`
   - Runs on PRs and pushes to `main` when the relevant release-story surfaces change.
   - Calls:
     - `bash tools/check-release-surfaces.sh`

4. The new guard immediately found a real remaining drift.
   - It flagged `.github/releases/v1.1.2.md` because it still said:
     - `external-drive install path`
   - Fixed in this session:
     - `.github/releases/v1.1.2.md`
     - changed to:
       - `external-drive setup path`

### Verification completed

1. Syntax-checked the new checker:
   - `bash -n tools/check-release-surfaces.sh`
2. Ran the checker locally before the fix:
   - it failed as intended and exposed the stale wording in `.github/releases/v1.1.2.md`
3. Fixed the flagged release-note wording drift.
4. Re-ran the checker:
   - result:
     - `Changelog copies are in sync.`
     - `No retired wording found on checked public release surfaces.`
     - `Release surfaces check passed.`
5. Confirmed the workflow file passed write-time YAML validation.

### Current status

The main goal of this track is now satisfied.

This repo now has a good small set of release-safety automations without drifting into a heavy framework:
- tag builds require a matching release-note file
- stale manifests are checked locally and in CI
- public release surfaces now have a small sanity guard for changelog sync + retired high-risk wording

### Why this was the right stopping point

The newly added guard was immediately useful because it caught a real leftover release-note inconsistency.

That is the kind of automation worth keeping here:
- small
- understandable
- low-noise
- directly tied to mistakes that already happened