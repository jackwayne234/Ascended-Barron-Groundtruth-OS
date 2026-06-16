# Update 12 — Automatic local logging documentation and wording alignment

Purpose:
Document the automatic local logging system more clearly and more honestly so users understand what is stored, where it stays, what the format is, and what responsibility still belongs to them.

Why this track exists:
- automatic local logging is one of the product's core trust surfaces
- the existing docs mention local logging, but not with enough detail
- the product owner does not want a built-in export workflow prioritized
- users should understand that logs stay local by default and can be moved with normal Linux commands if they want
- users should also be told plainly that redaction is best-effort and they remain responsible for reviewing sensitive data before training or fine-tuning

## Work completed in this track

Date: 2026-06-16

### 1. README logging section expanded into a dedicated automatic local logging section

What changed:
- clarified that logging is automatic and local-first
- clarified that logs stay on the running system or removable drive by default
- clarified that users can move/copy logs with normal Linux commands or their own shortcut app
- clarified that the main format is JSONL
- described the main categories of records in plain English
- clarified that the sample export is an example of downstream format, not a promise of a built-in export workflow

### 2. Getting Started logging section fleshed out

What changed:
- expanded the first-run explanation of logging beyond a one-paragraph mention
- explained that the OS does not automatically upload logs
- explained the JSONL shape at a high level
- described the same local-first / user-responsibility posture in beginner-facing language

### 3. Sensitive-data responsibility documented explicitly

What changed:
- added clear wording that built-in redaction is best-effort only
- added clear wording that the user remains responsible for reviewing and removing sensitive data before training, fine-tuning, or sharing logs with another tool/service

## Verification completed in this track

Commands run successfully:

```sh
bash tools/check-release-surfaces.sh
```

Additional verification:
- read back the edited README logging section
- read back the edited Getting Started logging section
- confirmed wording now matches the owner decision: local automatic logging yes, built-in export workflow not prioritized

## Outcome of this track

This documentation/wording track is complete.

It tightened one of the product's most important trust surfaces without adding new dashboard workflow surface area.