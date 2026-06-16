# GroundTruth OS release checklist

Use this checklist before every public tag/release.

This document is the repo's release gate for current GroundTruth OS public releases.
It is meant to be run, not just read.

## Where this lives and why

This checklist lives in `docs/` because it is project process, not only workflow machinery.
It needs to stay easy to read and update alongside README, Getting Started, changelog, and release-note work.

## Release rule

Do not tag a new public release until every blocker check below passes.

## Inputs for a release pass

Before you start, decide the release version:

```sh
version=vX.Y.Z
```

Replace `vX.Y.Z` with the real tag, for example `v1.1.3`.

## Blockers before tagging

### 1. Repo state is understood

Commands:

```sh
git status --short --branch
git remote -v
```

Pass when:
- you are on the intended branch
- you understand every modified file
- nothing surprising is present

Block if:
- the repo has unexplained changes
- you are on the wrong branch
- release work is mixed with unrelated edits

### 2. Required public docs match the actual product

Files to check:
- `README.md`
- `docs/GETTING-STARTED.md`
- `CHANGELOG.md`
- `airootfs/usr/local/share/ai-os/CHANGELOG.md`
- `.github/releases/${version}.md`

Reference workflow:
- `docs/RELEASE-STORY-WORKFLOW.md`

Pass when:
- visible docs match the current UI/install/update behavior
- release wording matches the actual product story for that version
- the shipped changelog copy matches the public changelog where it should
- any user-facing flow change has been walked through with the change-surface map from `docs/RELEASE-STORY-WORKFLOW.md`

Block if:
- docs still mention removed buttons or old workflows
- release wording does not match the actual UI
- the shipped changelog copy drifted from the intended public story
- a user-facing workflow changed but the matching release-story files were not updated in the same pass

### 3. Matching release-note file exists

Command:

```sh
test -f ".github/releases/${version}.md"
```

Pass when:
- the file exists for the exact tag you plan to publish

Block if:
- `.github/releases/${version}.md` is missing

Note:
- tag builds now fail if this file is missing, but do not wait for CI to tell you that.

### 4. Terminology and visible wording are consistent

Suggested scan:

```sh
rg -n "live USB|Work with AI|thumbdrive|persistent OS|open in terminal button|external-drive install path" README.md docs CHANGELOG.md airootfs/usr/local/share/ai-os .github/releases
```

Reference:
- `docs/TERMINOLOGY.md`

Pass when:
- current public wording uses the preferred terms
- any old wording that remains is clearly historical on purpose

Block if:
- current public docs or current release notes use retired wording by accident

### 5. Manifest is refreshed when shipped files changed

Rule:
- if anything under these managed roots changed, refresh the manifest:
  - `airootfs/usr/local/share/ai-os/`
  - `airootfs/usr/local/lib/ai-os/`
  - `airootfs/usr/local/bin/` for the OS's own launchers (`ai-os-*`, `start-ai-os-*`)
- generated version markers are excluded:
  - `INSTALLED_REV`
  - `INSTALLED_VERSION`
- the manifest file itself is excluded from the generated file list

Commands:

```sh
bash tools/check-manifest.sh
bash tools/gen-manifest.sh
```

Pass when:
- `bash tools/check-manifest.sh` reports that `MANIFEST.sha256` is current
- `airootfs/usr/local/share/ai-os/MANIFEST.sha256` matches the current managed shipped-file set

Block if:
- `bash tools/check-manifest.sh` reports a stale manifest
- shipped files changed but the manifest was not refreshed

### 6. Dashboard integrity checks pass

Command:

```sh
bash tools/check-dashboard-integrity.sh
```

Reference:
- `docs/DASHBOARD-STRUCTURE.md`

Pass when:
- the launcher compiles cleanly
- every `dashboard/*.py` module compiles cleanly
- the smoke harness boots the modularized dashboard and all smoke steps pass

Block if:
- any dashboard compile/import error appears
- the smoke harness fails to boot or exercise the modularized dashboard

### 7. Shell syntax checks pass

Command:

```sh
for f in build.sh bootstrap-updater.sh tools/gen-manifest.sh airootfs/usr/local/bin/ai-os-update airootfs/usr/local/bin/ai-os-rollback airootfs/usr/local/bin/ai-os-install-to-disk; do if [ -f "$f" ]; then bash -n "$f" || exit 1; fi; done
```

Pass when:
- every relevant shell script parses cleanly

Block if:
- any shell syntax error appears

### 8. Git diff is intentional before tagging

Commands:

```sh
git status --short
git diff -- README.md docs/GETTING-STARTED.md CHANGELOG.md airootfs/usr/local/share/ai-os/CHANGELOG.md .github/releases airootfs/usr/local/share/ai-os/MANIFEST.sha256
```

Pass when:
- the release-critical diff is intentional and complete

Block if:
- a required release file is missing from the diff
- unrelated changes are still mixed in

### 9. Working tree is clean before the tag is created

Command:

```sh
git status --short
```

Pass when:
- the tree is clean after the intended release commit(s)

Block if:
- uncommitted changes remain when you are about to tag

## Build and publish

For a tagged release, the workflow is:
- `.github/workflows/build-release-iso.yml`

It triggers on:
- `push` tags matching `v*`
- manual dispatch with a version input

## Blockers after the build starts

### 10. GitHub Actions run succeeds

Suggested commands:

```sh
gh run list --workflow "Build release ISO" --limit 5
gh run view --log-failed
```

Pass when:
- the intended run reaches `success`

Block if:
- the build fails
- the wrong version was built
- the release workflow publishes no assets

### 11. Release exists and has the expected assets

Suggested command:

```sh
gh release view "$version"
```

Pass when:
- the release exists
- it includes the ISO asset
- it includes `SHA256SUMS`
- the release body is the matching `.github/releases/${version}.md` story

Block if:
- the release is missing
- either asset is missing
- the release body/tag/version is wrong

### 12. Downloaded asset verifies locally

Suggested commands:

```sh
mkdir -p /tmp/gtos-release-check
cd /tmp/gtos-release-check
gh release download "$version"
sha256sum -c SHA256SUMS
```

Pass when:
- checksum verification reports `OK`

Block if:
- the checksum fails
- the wrong ISO filename is present

## Strong recommended post-build checks

These are not always required for every tiny wording release, but they should be treated as release blockers whenever the release changed boot behavior, install/update behavior, shipped payload, or user-visible dashboard behavior.

### 13. Inspect the built artifact for release-critical content

Examples:
- confirm the expected versioned ISO filename exists
- confirm release-critical files are present in the built payload
- confirm removed wording/buttons are actually absent when that was the point of the release
- confirm boot-parameter changes are really inside the ISO when boot behavior changed

If the release is about a specific live-laptop fix or a boot/install/update change, do not stop at "GitHub build succeeded." Verify the artifact itself.

### 14. Live hardware verification when the release changed live behavior

Examples:
- updater flow
- dashboard/window behavior
- install/setup behavior
- boot parameters
- visible logging/training capture behavior

If the release claim is about real laptop behavior, use a real laptop as the final gate when available.

## Non-blocking notes

These should be recorded, but they do not automatically stop a release unless they change the public story or the artifact's safety/usability.

Examples:
- future polish ideas
- deeper automation ideas
- optional heading/style consistency work
- internal comment cleanup

## Short release pass summary template

Use something like this in notes or handoff text:

```text
Release version: vX.Y.Z
Docs/UI match: PASS/FAIL
Release note file exists: PASS/FAIL
Manifest refreshed: PASS/FAIL
Dashboard integrity: PASS/FAIL
Shell syntax: PASS/FAIL
Git tree clean before tag: PASS/FAIL
GitHub build: PASS/FAIL
Release assets present: PASS/FAIL
SHA256SUMS verified locally: PASS/FAIL
Artifact/live verification: PASS/FAIL or N/A
Blockers remaining: ...
Non-blocking notes: ...
```
