# Update 11 — Post-release maintenance after v1.1.3

Purpose:
Capture the first follow-on maintenance pass after the v1.1.3 release and live-laptop acceptance.

Why this track existed:
After v1.1.3 was released and accepted on the real laptop, the next highest-value work was no longer emergency product behavior. It was repo/release maintenance and conservative post-modularization cleanup:
- remove the clearest future CI risk
- make the launcher thinner where the split had already proved stable
- explicitly decide whether to split the remaining `Dashboard` class further
- resolve the remaining historical GitHub release-body decision
- tighten/document the background-layer slice without reopening unnecessary churn

## Work completed in this track

Date: 2026-06-16

### 1. GitHub Actions Node 20 deprecation risk addressed

Ground truth from the successful `v1.1.3` build run:
- GitHub annotated the run with a Node 20 deprecation warning for:
  - `actions/checkout@v4`
  - `actions/upload-artifact@v4`
  - `softprops/action-gh-release@v2`

What changed:
- `.github/workflows/build-release-iso.yml`
  - `actions/checkout@v4` → `actions/checkout@v6`
  - `actions/upload-artifact@v4` → `actions/upload-artifact@v7`
  - `softprops/action-gh-release@v2` → `softprops/action-gh-release@v3`
- `.github/workflows/check-dashboard-integrity.yml`
  - `actions/checkout@v4` → `actions/checkout@v6`
- `.github/workflows/check-manifest.yml`
  - `actions/checkout@v4` → `actions/checkout@v6`
- `.github/workflows/check-release-surfaces.yml`
  - `actions/checkout@v4` → `actions/checkout@v6`

Verification completed:
- all workflow YAML parsed successfully
- the workflow files remained syntactically valid after the version updates

### 2. Post-modularization launcher cleanup completed

What changed:
- Added `airootfs/usr/local/share/ai-os/dashboard/background_layer.py`
- Moved the background-window / desktop-layer behavior out of `ai-os-dashboard.py` into that module
- Updated the launcher to import `keep_dashboard_in_background` from the extracted module

Why this counted as the right cleanup now:
- it made the launcher thinner again
- it extracted a clearly bounded support slice
- it avoided renaming the shipped entrypoint or churning the public path assumptions

### 3. Decision made: keep one main `Dashboard` class for now

Decision:
- do not split the remaining `Dashboard` class further yet

Reason:
- the post-modularization release was built successfully
- the release updated successfully on the real laptop
- real post-update use looked good
- there is not yet enough evidence that another controller/screen split would justify more churn in shipped wiring and verification surface area

Where this decision is now documented:
- `docs/DASHBOARD-STRUCTURE.md`

### 4. Historical published GitHub release bodies aligned

Decision:
- do not leave the older published GitHub release bodies as mismatched historical accidents
- normalize them to the checked-in `.github/releases/` files and consistent release titles

What changed live on GitHub:
- release titles were normalized to `GroundTruth OS vX.Y.Z`
- published bodies for these tags were updated from the checked-in files:
  - `v1.0.0`
  - `v1.0.1`
  - `v1.0.2`
  - `v1.1.0`
  - `v1.1.1`
  - `v1.1.2`

Observed result after the change:
- `gh release list --limit 10` showed a consistent title format for every current tag

### 5. Background-window semantics track tightened and documented

What changed:
- the background-layer logic is now its own extracted module instead of anonymous bottom-of-file launcher code
- `docs/DASHBOARD-STRUCTURE.md` now records the practical status of the background behavior and the decision rule for future work

Current documented posture:
- real visible behavior is the primary release gate
- EWMH/X11 details remain supporting evidence, not the sole ship gate
- future sessions should reopen deeper background/EWMH work only if a real visible regression returns

## Verification completed in this track

Commands run successfully:

```sh
bash tools/gen-manifest.sh
bash tools/check-dashboard-integrity.sh
bash tools/check-manifest.sh
bash tools/check-release-surfaces.sh
```

Additional verification:
- all workflow YAML files parsed successfully
- dashboard integrity smoke harness passed
- `MANIFEST.sha256` was regenerated and confirmed current
- public/shipped release surfaces still passed the wording checks
- GitHub release titles now read consistently in `gh release list`

Observed dashboard-integrity result:
- launcher present
- dashboard module count: 25
- compile check passed
- smoke harness result:
  - `all_steps_passed: true`
  - `steps: 10`
  - `failures: 0`

## Outcome of this track

This maintenance track is complete.

It closed the five most important post-v1.1.3 follow-up items:
1. Node 20 deprecation risk reduced
2. launcher cleanup completed in a conservative slice
3. further-split decision explicitly made
4. historical published release-body mismatch resolved
5. background-layer slice isolated and documented

## Recommended next-session prompt

Open `updates/update11.md` first if you want context on the post-v1.1.3 maintenance pass.

After that, do not assume another maintenance track is needed by default. Start from a real current product need.
