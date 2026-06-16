# GroundTruth OS release-story alignment workflow

Use this workflow whenever a change affects a user-facing flow, visible button, install path, update path, release story, or shipped help text.

The rule is simple:

If a release changes what a user sees or does, update the matching docs and release surfaces in the same pass.

## Core rule

Do not treat UI/code changes and doc/release-story changes as separate chores.

Ship them together.

## What counts as a release-story change

Examples:
- a dashboard button appears, disappears, or changes meaning
- install behavior changes
- update behavior changes
- task/project-terminal workflow changes
- logging/privacy wording changes
- visible terminology changes
- shipped sample/help text changes
- anything that changes what the release page should promise

## The change-surface map

When a user-facing flow changes, check these together in one pass:

1. `README.md`
   - top-level product story
   - what the OS is
   - what the normal workflow is
   - install/update/privacy wording

2. `docs/GETTING-STARTED.md`
   - step-by-step user flow
   - install/setup/update instructions
   - visible button/workflow descriptions

3. `CHANGELOG.md`
   - public release story
   - what changed for users

4. `airootfs/usr/local/share/ai-os/CHANGELOG.md`
   - shipped in-app/public-facing changelog copy

5. `.github/releases/vX.Y.Z.md`
   - per-tag GitHub release body

6. `docs/TERMINOLOGY.md`
   - if wording guidance itself needs to change

7. Shipped sample/help docs under `airootfs/` when affected
   - example project notes
   - bundled helper docs
   - shipped sample text

8. `airootfs/usr/local/share/ai-os/MANIFEST.sha256`
   - refresh if shipped files under the managed roots changed

## If UI changed, update these files

Use this small list as the first reflex:

- `README.md`
- `docs/GETTING-STARTED.md`
- `CHANGELOG.md`
- `airootfs/usr/local/share/ai-os/CHANGELOG.md`
- `.github/releases/vX.Y.Z.md`
- any shipped sample/help doc touched by the same workflow
- `airootfs/usr/local/share/ai-os/MANIFEST.sha256` if shipped files changed

## Order of operations

Use this order unless there is a good reason not to:

1. Update the actual code/UI/workflow behavior.
2. Update `README.md` so the top-level story is right.
3. Update `docs/GETTING-STARTED.md` so the step-by-step flow matches.
4. Update `CHANGELOG.md` and the shipped changelog copy together.
5. Update the matching `.github/releases/vX.Y.Z.md` file.
6. Update shipped sample/help docs if the same flow appears there.
7. Refresh `MANIFEST.sha256` if shipped files changed.
8. Run the release checklist / manifest check before tagging.

## Blocker rule

If a user-facing workflow changed but one of the matching public/shipped release-story files was left behind, that is a release blocker.

## Lightweight verification

Suggested checks:

```sh
git diff -- README.md docs/GETTING-STARTED.md CHANGELOG.md airootfs/usr/local/share/ai-os/CHANGELOG.md .github/releases docs/TERMINOLOGY.md airootfs/usr/local/share/ai-os/MANIFEST.sha256
```

```sh
bash tools/check-manifest.sh
```

```sh
rg -n "live USB|Work with AI|thumbdrive|persistent OS|open in terminal button|external-drive install path" README.md docs CHANGELOG.md airootfs/usr/local/share/ai-os .github/releases
```

## Verification implications after modularization

If the dashboard launcher or anything under `airootfs/usr/local/share/ai-os/dashboard/` changes, treat it as a modular dashboard verification pass, not just a single-file edit.

Run:

```sh
bash tools/check-dashboard-integrity.sh
```

Reference:
- `docs/DASHBOARD-STRUCTURE.md`

This verifies:
- the shipped launcher still imports correctly
- every extracted module still compiles
- the dashboard still boots and survives the smoke harness under Xvfb

## Practical examples

### Example: install path wording changed

Update together:
- README install wording
- Getting Started install section
- public changelog
- shipped changelog
- release note for the tag
- terminology guide if the preferred term changed
- manifest if shipped files changed

### Example: dashboard button removed

Update together:
- README workflow description
- Getting Started steps
- changelogs
- release note
- any shipped sample/help doc that still mentions the button
- manifest if shipped files changed

### Example: updater behavior changed

Update together:
- README update section
- Getting Started update section
- changelogs
- release note
- any shipped help text mentioning the updater
- manifest if shipped files changed

## Why this exists

This project is unusually sensitive to wording drift.

A technically correct code change is still not release-ready if the README, Getting Started guide, shipped changelog, and release body tell a different story.
