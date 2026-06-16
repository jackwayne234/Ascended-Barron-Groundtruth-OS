# Update 7 — Release-story alignment workflow

Purpose:
Make sure any UI or workflow change automatically triggers the right doc/release-note updates in the same development pass.

Why this matters:
This project is very sensitive to wording drift. If a dashboard button disappears or the install path changes, the release story must change everywhere at once.

Core idea:
When a release changes a user-facing flow, update these together in one pass:
- README
- Getting Started
- public changelog
- shipped in-app changelog
- matching GitHub release note
- any shipped sample or helper doc affected by the same workflow

Goals for a future session:
1. Turn this into a documented workflow rule.
2. Decide where that rule should live.
3. Add a small “if UI changed, update these files” list.
4. Make this part of the release checklist and contribution discipline.

Likely good home:
- `docs/release-workflow.md`
- or a release checklist document
- or `.github/` docs if you want it closer to release machinery

Good outcome:
A clear “change surface map” so a future session immediately knows what files must move together when the UI changes.

Recommended next-session prompt:
Open `updates/update7.md` first. Create a documented release-story alignment workflow so future UI/install/update changes automatically trigger the right docs, changelog, shipped-doc, and release-note updates.

## Progress snapshot — 2026-06-16

What was completed in this session:

1. Chose the workflow home.
   - Decision: put the rule in `docs/RELEASE-STORY-WORKFLOW.md`
   - Reason: this is a repo workflow/documentation discipline rule, not just CI machinery, so it belongs with the maintained docs.

2. Created the release-story alignment workflow document.
   - Added `docs/RELEASE-STORY-WORKFLOW.md`
   - The document now defines:
     - the core rule: if a release changes what a user sees or does, update the matching docs/release surfaces in the same pass
     - what counts as a release-story change
     - a change-surface map
     - a short `if UI changed, update these files` list
     - an order of operations
     - a blocker rule
     - lightweight verification commands
     - practical examples for install/update/button changes

3. Turned the idea into an explicit change-surface map.
   - The workflow now names the files that should move together when a user-facing flow changes:
     - `README.md`
     - `docs/GETTING-STARTED.md`
     - `CHANGELOG.md`
     - `airootfs/usr/local/share/ai-os/CHANGELOG.md`
     - `.github/releases/vX.Y.Z.md`
     - `docs/TERMINOLOGY.md` when wording guidance itself changes
     - any shipped sample/help doc under `airootfs/` affected by the same workflow
     - `airootfs/usr/local/share/ai-os/MANIFEST.sha256` when shipped files changed

4. Integrated the rule into the release checklist.
   - Updated `docs/RELEASE-CHECKLIST.md`
   - Added:
     - a reference to `docs/RELEASE-STORY-WORKFLOW.md`
     - a pass condition requiring user-facing flow changes to be walked through with the change-surface map
     - a blocker condition for changing a user-facing workflow without updating the matching release-story files in the same pass

### Current status

The main goal of this track is now satisfied:
- there is a documented workflow rule for release-story alignment
- there is now a small explicit `if UI changed, update these files` map
- the rule is connected to release discipline through the release checklist instead of living only as a standalone note

### Optional future follow-on

1. If contributor-facing docs grow later, consider linking both `docs/RELEASE-STORY-WORKFLOW.md` and `docs/RELEASE-CHECKLIST.md` from a contributor/release section.
2. If future UI areas become more complex, expand the examples section rather than adding brittle automation.
3. Keep this workflow aligned with future terminology, manifest, and release-note discipline changes from the neighboring update tracks.