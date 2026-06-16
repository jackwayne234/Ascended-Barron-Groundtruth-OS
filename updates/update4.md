# Update 4 — Repo-wide terminology consistency

Purpose:
Clean up wording drift across the repository so the same concepts are described the same way everywhere.

Why this matters:
The project now has cleaner public docs, but wording drift can creep back in through sample files, comments, release notes, helper text, or future docs.

Current preferred terms:
- removable media
- external-drive setup path
- advanced terminal installer
- project terminal
- local workflow logging
- bring your own AI

Terms to watch for:
- live USB
- Install to disk
- Work with AI
- thumbdrive
- persistent OS
- open in terminal button

Goals for a future session:
1. Search the full repo for stale terms.
2. Separate public-facing text from internal code comments.
3. Update user-facing text first.
4. Only update internal comments/identifiers where it improves clarity without causing churn.
5. Produce a small style guide for future wording.

Suggested outputs:
- a short glossary file or section in docs
- a list of allowed/preferred terms
- a list of retired or discouraged phrases

Caution:
- do not force wording changes inside code identifiers if it creates rename churn without user benefit
- prioritize visible user text, shipped docs, release notes, and samples first

Recommended next-session prompt:
Open `updates/update4.md` first. Run a repo-wide terminology sweep, separate public wording from internal code wording, and create a small preferred-terms guide so future edits stay consistent.

## Sweep snapshot — 2026-06-16

What was checked:
1. Repo-wide search for discouraged phrases:
   - `live USB`
   - `Install to disk`
   - `Work with AI`
   - `thumbdrive`
   - `persistent OS`
   - `open in terminal button`
2. Repo-wide search for preferred terms:
   - `removable media`
   - `external-drive setup path`
   - `advanced terminal installer`
   - `project terminal`
   - `local workflow logging`
   - `bring your own AI`
3. User-facing docs first, then shipped docs/changelogs, then historical/session notes

### Findings

1. The repo was already mostly clean in current public docs.
   - Most obvious stale terms had already been removed from the active README / Getting Started / release-note surfaces.
   - The remaining drift was small and concentrated in a few visible files.

2. The main user-facing wording drifts found in this pass were:
   - `docs/GETTING-STARTED.md`
     - `Optional external-drive install path`
   - `README.md`
     - `local training log`
   - `CHANGELOG.md`
     - `external-drive install path`
   - `airootfs/usr/local/share/ai-os/CHANGELOG.md`
     - `external-drive install path`

3. The discouraged terms still found after cleanup were mostly acceptable leftovers.
   - They now mainly appear in:
     - this tracking file
     - `docs/TERMINOLOGY.md` as retired/discouraged examples
     - `updates/update1.md` and `updates/update3.md` as historical session/report text
   - That is acceptable because those files are describing wording history, not serving as the current public product surface.

### Changes completed in this session

1. Updated visible user-facing wording:
   - `docs/GETTING-STARTED.md`
     - `Optional external-drive install path` → `Optional external-drive setup path`
   - `README.md`
     - `local training log` phrasing → `local workflow logging`

2. Updated visible changelog wording:
   - `CHANGELOG.md`
     - `external-drive install path` → `external-drive setup path`
   - `airootfs/usr/local/share/ai-os/CHANGELOG.md`
     - `external-drive install path` → `external-drive setup path`

3. Added a small terminology guide:
   - `docs/TERMINOLOGY.md`
   - Includes:
     - preferred terms
     - discouraged/retired terms
     - short usage notes
     - a simple editing rule of thumb

4. Refreshed the shipped manifest because a shipped file changed:
   - `airootfs/usr/local/share/ai-os/MANIFEST.sha256`

### Verification completed

1. Re-searched the repo for discouraged terms after the edits.
2. Confirmed the remaining hits are now limited to:
   - the terminology guide itself
   - update-tracking/history files where old wording is being discussed on purpose
3. Confirmed the shipped manifest was regenerated after changing the shipped changelog copy.

### Current status

The main terminology-consistency pass for current user-facing wording is in a good finished state.

What remains is optional future polish only:
1. continue using `docs/TERMINOLOGY.md` as the wording reference for future doc/release/UI edits
2. only touch internal code comments/identifiers when the clarity gain is worth the churn
3. preserve historically accurate old wording when documenting older releases or older UI states