# GroundTruth OS terminology guide

Use this file to keep user-facing wording consistent across README text, Getting Started, changelogs, release notes, shipped docs, and sample project text.

## Preferred terms

- removable media
- live boot from removable media
- external-drive setup path
- advanced terminal installer
- project terminal
- local workflow logging
- bring your own AI

## Preferred usage notes

### Removable-media wording

Prefer:
- `removable media`
- `live boot from removable media`

Avoid in current public wording unless you are quoting historical release text:
- `live USB`
- `thumbdrive`
- `persistent OS`

### External-drive wording

Prefer:
- `external-drive setup path`
- `advanced terminal installer`
- ``sudo ai-os-install-to-disk``

Avoid in current public wording unless the historical version really used it:
- `Install to disk`
- `external-drive install path`

Notes:
- Use `Install to disk` only when you are intentionally preserving the visible historical wording of an older release.
- For current docs, use `external-drive setup path` for the concept and `advanced terminal installer` for the command-driven workflow.

### Task/AI workflow wording

Prefer:
- `project terminal`
- `bring your own AI`
- `local workflow logging`

Avoid in current public wording unless discussing old UI/history:
- `Work with AI`
- `open in terminal button`
- `local training log` when `local workflow logging` is the clearer concept

## Editing rule of thumb

1. Update visible user-facing wording first.
2. Keep historical release notes historically accurate.
3. Do not rename code identifiers just to chase wording consistency.
4. If a phrase appears in shipped docs under `airootfs/`, remember to refresh `airootfs/usr/local/share/ai-os/MANIFEST.sha256` in the same pass.
