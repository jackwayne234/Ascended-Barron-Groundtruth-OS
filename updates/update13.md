# Update 13 — Shipped sample-project alignment toward useful app ideas

Purpose:
Replace the weaker shipped sample task with something more immediately useful and more aligned with the product's app-building loop, while keeping the new idea documented rather than preinstalled.

Why this track exists:
- the older "Build a simple personal webpage" sample was not the strongest first-run fit
- it leaned toward web/publishing complexity instead of a small useful personal app
- the product owner wants the three examples to feel like things that could naturally turn into dashboard app buttons later
- a simple daily journal app is easier to understand, more broadly useful, and a better fit for the core loop: task -> project folder -> ground-truth -> build something local

## Work completed in this track

Date: 2026-06-16

### 1. Replaced the webpage sample across the main user-facing surfaces

What changed:
- `README.md`
  - sample list now says `Build a simple daily journal app`
- `docs/GETTING-STARTED.md`
  - sample list now says `Build a simple daily journal app`
- the journal app is now presented as a documented example idea rather than as a shipped sample project

### 2. Final decision: keep the journal app as a documented example, not an installed sample

What changed:
- removed the temporary journal task entry from `airootfs/home/barron/workspace/Eisenhower priority matrix to do list/tasks.json`
- removed the temporary shipped folder so the example lives in docs instead of as preinstalled sample content

Why this matters:
- this keeps the product from spending too much effort on installed sample content
- the idea is still available to users without pretending it ships as a ready-made project folder
- the sample still naturally suggests a future local app that could be placed on a dashboard app button

## Verification completed in this track

Commands run successfully:

```sh
bash tools/check-release-surfaces.sh
```

Additional verification:
- searched the repo for the old personal-webpage sample wording and confirmed the main user-facing surfaces were updated
- confirmed the shipped workspace no longer contains the journal sample folder
- read back the updated README / Getting Started wording to confirm the journal app is now documented as an example idea, not an installed sample

## Outcome of this track

This sample-alignment track is complete.

The three-example set is now:
1. `Plan a 3-day weekend trip` — completed planning example
2. `Build a simple daily journal app` — useful example idea documented in the docs, not preinstalled
3. `Add a feature to my dashboard` — self-modification demo