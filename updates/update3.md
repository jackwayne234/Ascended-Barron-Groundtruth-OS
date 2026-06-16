# Update 3 — Release-note and release-body consistency

Purpose:
Make GitHub release bodies consistent across tags and make sure every tagged release has a matching `.github/releases/vX.Y.Z.md` file that accurately reflects the product at that version.

Why this matters:
Release notes are part of the public product surface. If they drift from the README, Getting Started guide, or actual UI, the project looks less trustworthy.

Goals for a future session:
1. Inspect `.github/releases/` for completeness and consistency.
2. Check that each release note matches the actual release story for that version.
3. Normalize tone, structure, and terminology across release-note files.
4. Decide on a standard release-note template for future tags.
5. If useful, add a guard so the release workflow fails when a matching release-note file is missing.

Suggested checks:
- every release note starts with a short summary
- every release note has a small "What's new" section
- every release note includes checksum verification text
- wording matches the product state for that release
- old UI/button references are not lingering in later releases

Possible automation later:
- a workflow check that confirms `.github/releases/${tag}.md` exists for tag builds
- optional lint check for required headings in release-note files

Do not do yet unless needed:
- do not rewrite historical releases to say things they did not say or promise at the time
- do not change the release workflow unless the new guard is clearly worth it

Recommended next-session prompt:
Open `updates/update3.md` first. Audit `.github/releases/` for completeness, consistency, and drift against the actual product story. If the release workflow should require matching release-note files, propose the safest way to add that guard.

## Audit snapshot — 2026-06-16

What was checked:
1. `.github/releases/` file inventory
2. Git tags present in the repo
3. Current release workflow note-resolution behavior
4. Release-note body consistency across `v1.1.0` to `v1.1.2`
5. Drift against current `README.md`, `docs/GETTING-STARTED.md`, and `CHANGELOG.md`
6. Published GitHub releases list

### Findings

1. `.github/releases/` is incomplete relative to the tagged history.
   - Present note files:
     - `v1.1.0.md`
     - `v1.1.1.md`
     - `v1.1.2.md`
   - Repo tags present:
     - `v1.0.0`
     - `v1.0.1`
     - `v1.0.2`
     - `v1.1.0`
     - `v1.1.1`
     - `v1.1.2`
   - Meaning:
     - `v1.0.0`, `v1.0.1`, and `v1.0.2` do not currently have matching `.github/releases/vX.Y.Z.md` files.

2. The release workflow currently hides missing release-note files instead of failing.
   - In `.github/workflows/build-release-iso.yml`, the `Resolve release notes` step does this:
     - tries `.github/releases/${version}.md`
     - if missing, falls back to `.github/releases/v1.1.0.md`
   - That means a future tag can publish with the wrong body instead of failing loudly.

3. The `v1.1.x` release notes are mostly aligned in terminology.
   - Good alignment seen with current docs/changelog wording:
     - `external-drive setup path`
     - `advanced terminal installer`
     - `sudo ai-os-install-to-disk`
     - `Update OS`
   - No obvious stale old-button wording was seen in the `v1.1.0` to `v1.1.2` files during this audit.

4. Structure is not fully normalized yet.
   - `v1.1.0` uses `## What's new`
   - `v1.1.1` uses `## What's changed`
   - `v1.1.2` uses `## What's new`
   - All three include checksum verification text.
   - Only `v1.1.0` currently includes an explicit `## Release verification` section.
   - `v1.1.0` also includes upgrade-path guidance for older users; `v1.1.1` and `v1.1.2` are much shorter.

5. Published releases exist for all six tags.
   - The GitHub release list includes `v1.0.0` through `v1.1.2`.
   - So the repo now has a mismatch between tagged/published release history and the checked-in `.github/releases/` file set.

### Assessment

Current state is acceptable for the existing `v1.1.x` notes, but not yet complete enough to claim that every tagged release has a matching checked-in release-note file.

The most important concrete problem is not wording drift inside `v1.1.x`; it is the missing checked-in files for `v1.0.0` to `v1.0.2` plus the workflow fallback that can silently publish the wrong release body.

### Safest next step

1. Add matching checked-in release-note files for:
   - `v1.0.0`
   - `v1.0.1`
   - `v1.0.2`
2. Normalize heading structure across the existing `v1.1.x` files without changing their historical claims.
3. After the missing files exist, replace the workflow fallback with a hard failure for missing `.github/releases/${version}.md` on tag builds.

## Progress log — 2026-06-16 completion pass

Completed in this session:

1. Added the missing checked-in release-note files:
   - `.github/releases/v1.0.0.md`
   - `.github/releases/v1.0.1.md`
   - `.github/releases/v1.0.2.md`

2. Preserved the historical product story instead of rewriting it into modern wording.
   - The new `v1.0.x` files keep the older release-era concepts where they mattered, including historical references such as:
     - `Install to disk`
     - the early experimental framing
     - the older updater/install transition story for `v1.0.2`

3. Normalized one obvious heading inconsistency in the `v1.1.x` set.
   - Changed `.github/releases/v1.1.1.md`
   - from `## What's changed`
   - to `## What's new`

4. Removed the dangerous workflow fallback in `.github/workflows/build-release-iso.yml`.
   - Old behavior:
     - if `.github/releases/${version}.md` was missing, the workflow silently fell back to `.github/releases/v1.1.0.md`
   - New behavior:
     - tag builds now fail loudly if the matching release-note file is missing
     - non-tag builds log the missing file but do not silently substitute the wrong release body

### Verification completed

1. Checked Git tags against `.github/releases/*.md`
   - tags present:
     - `v1.0.0`
     - `v1.0.1`
     - `v1.0.2`
     - `v1.1.0`
     - `v1.1.1`
     - `v1.1.2`
   - matching checked-in release-note files now exist for all six tags
   - no missing tags
   - no extra unmatched files

2. Read back the patched workflow section
   - confirmed the tag-build path now errors on a missing `.github/releases/${version}.md`

### Current status

The main release-note completeness gap described earlier in this file is now closed for the current tag set.

What remains here is lighter follow-on polish rather than the original missing-file problem:
1. decide whether older published GitHub release bodies should be manually updated to match the new checked-in files, or left as historical artifacts
2. optionally add a lightweight heading/shape lint later if the team wants it

## Final polish pass — 2026-06-16

Completed in this pass:

1. Standardized the remaining update-section headings for consistency.
   - `.github/releases/v1.1.0.md`
     - `## For v1.0.2 users` → `## Updating from v1.0.2`
     - `## For v1.0.0 / v1.0.1 users` → `## Updating from v1.0.0 / v1.0.1`
   - `.github/releases/v1.1.2.md`
     - `## For users updating from v1.1.x` → `## Updating from v1.1.x`

2. Left the rest of the note bodies alone.
   - No historical claims were changed.
   - No new release-verification claims were added where they were not already present.
   - The pass stayed structure-only.

### Result after final polish

The checked-in release-note set is now in a good finished state for the current repo:
- every current tag has a matching `.github/releases/vX.Y.Z.md` file
- the most dangerous workflow fallback is gone
- the main section naming is now more consistent across the note set
- remaining differences are mostly release-specific content depth, which is acceptable as historical variation

### Suggested standard release-note shape for future tags

1. Title: `# vX.Y.Z release notes`
2. One-line summary
3. `## What's new`
4. Optional `## Updating from ...` section when needed
5. `## Verify download`
6. Optional `## Release verification` section when a release had a specific verification gate

### Scope caution

Do not rewrite historical notes to invent claims they did not make at the time.

Safe cleanup here means:
- add missing per-tag files
- normalize headings/structure where truth is unchanged
- make the workflow fail when a tag-specific note file is missing
- keep release wording aligned with the actual product story for that version