#!/usr/bin/env bash
# make-release.sh — cut a GroundTruth OS release, repeatably (maintainer-only).
#
# One command does: validate the version, create a SIGNED tag, build the ISO
# FROM that tag, checksum it, GPG-SIGN the checksum file, and scaffold notes —
# then tell you exactly what to push/publish. (Q14/Q35/Q48/Q53)
#
# Usage:
#   REL_KEY_FPR=<fingerprint> tools/make-release.sh v1.1.0
#   tools/make-release.sh v1.1.0 --no-build      # tag+sign only (build later on Arch)
#
# The version is an explicit, validated argument (Q48) — it must be a clean
# semver step above the latest existing tag.
set -euo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
KEY_FPR="${REL_KEY_FPR:-}"
DO_BUILD=1
VERSION=""

say(){ printf '%s\n' "$*"; }
die(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }

for a in "$@"; do
  case "$a" in
    --no-build) DO_BUILD=0 ;;
    v[0-9]*)    VERSION="$a" ;;
    *)          die "unknown argument: $a" ;;
  esac
done
[ -n "$VERSION" ] || die "usage: make-release.sh vMAJOR.MINOR.PATCH [--no-build]"

# ---- validate the version string + that it's a clean bump (Q48) -------------
echo "$VERSION" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$' || die "version must look like v1.2.3 (got '$VERSION')."
git -C "$REPO" rev-parse "$VERSION" >/dev/null 2>&1 && die "tag $VERSION already exists."
LATEST="$(git -C "$REPO" tag --list 'v[0-9]*' | sort -V | tail -n1)"
if [ -n "$LATEST" ]; then
  HIGHER="$(printf '%s\n%s\n' "$LATEST" "$VERSION" | sort -V | tail -n1)"
  [ "$HIGHER" = "$VERSION" ] && [ "$VERSION" != "$LATEST" ] || die "$VERSION is not higher than the latest tag $LATEST."
fi

# ---- keep the managed-files manifest fresh (Q28/Q40) ------------------------
say "==> refreshing managed-files manifest"
"$REPO/tools/gen-manifest.sh" >/dev/null

# ---- clean working tree on main ---------------------------------------------
if [ -n "$(git -C "$REPO" status --porcelain)" ]; then
  git -C "$REPO" status --short
  die "working tree not clean — commit the above first (e.g. a refreshed MANIFEST.sha256), then re-run."
fi
BRANCH="$(git -C "$REPO" rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" = "main" ] || say "WARNING: you are on '$BRANCH', not 'main'."

# ---- signing key ------------------------------------------------------------
if [ -n "$KEY_FPR" ]; then
  command -v gpg >/dev/null 2>&1 || die "gpg not installed but REL_KEY_FPR is set."
  gpg --list-secret-keys "$KEY_FPR" >/dev/null 2>&1 || die "no secret key for fingerprint $KEY_FPR."
else
  say "WARNING: REL_KEY_FPR not set — the tag and checksums will NOT be signed."
  say "         (Signed releases are required for verified updates; Q5/Q39.)"
  read -rp "Continue UNSIGNED anyway? Type 'yes': " ans
  [ "$ans" = "yes" ] || die "aborted (set REL_KEY_FPR to sign)."
fi

# ---- create the tag (signed if we have a key) -------------------------------
say "==> tagging $VERSION"
if [ -n "$KEY_FPR" ]; then
  git -C "$REPO" -c user.signingkey="$KEY_FPR" tag -s "$VERSION" -m "Ascended Barron: GroundTruth OS $VERSION"
else
  git -C "$REPO" tag -a "$VERSION" -m "Ascended Barron: GroundTruth OS $VERSION"
fi

if [ "$DO_BUILD" = 0 ]; then
  say ""
  say "Tag $VERSION created (no build). Next: build on an Arch box, then push:"
  say "    git push origin main && git push origin $VERSION"
  exit 0
fi

# ---- build the ISO FROM the tag ---------------------------------------------
command -v mkarchiso >/dev/null 2>&1 || die "mkarchiso not found — run --no-build here and build on an Arch system."
[ "$(id -u)" = 0 ] || die "the build step needs root: sudo -E REL_KEY_FPR=$KEY_FPR tools/make-release.sh $VERSION"

OUT="${OUT:-$REPO/../release}"
mkdir -p "$OUT"
say "==> building ISO from $VERSION (this takes a while)…"
git -C "$REPO" -c advice.detachedHead=false checkout "$VERSION"
"$REPO/build.sh" --out "$OUT"
git -C "$REPO" checkout "$BRANCH"

ISO="$(ls -t "$OUT"/*.iso 2>/dev/null | head -n1)"
[ -n "$ISO" ] || die "build finished but no ISO found in $OUT."

# ---- checksum + SIGN the checksum file (Q53) --------------------------------
say "==> checksums"
( cd "$OUT" && sha256sum "$(basename "$ISO")" > SHA256SUMS )
if [ -n "$KEY_FPR" ]; then
  say "==> signing SHA256SUMS"
  ( cd "$OUT" && gpg --local-user "$KEY_FPR" --armor --detach-sign --output SHA256SUMS.asc SHA256SUMS )
fi

say ""
say "✓ Release $VERSION staged in: $OUT"
ls -lh "$OUT"/*.iso "$OUT"/SHA256SUMS* 2>/dev/null || true
say ""
say "NEXT:"
say "  git push origin main && git push origin $VERSION"
say "  gh release create $VERSION $OUT/$(basename "$ISO") $OUT/SHA256SUMS${KEY_FPR:+ $OUT/SHA256SUMS.asc} \\"
say "     --title \"Ascended Barron: GroundTruth OS $VERSION\" --notes-file <notes>"
