#!/usr/bin/env bash
# Build Ascended Barron: GroundTruth OS — canonical staging + ISO build.
#
# This repo is an archiso profile OVERLAY on Arch's official `releng` profile
# (see BUILD.md). This script implements the build contract:
#   1. copy the version-matched releng base
#   2. overlay this repo (profiledef.sh, pacman.conf, airootfs/) — ours win
#   3. union the package lists (no live-boot essential dropped)
#   4. keep releng's bootloader dirs (syslinux/grub/efiboot)
#   5. run mkarchiso
# then hash-verify that the staged payload matches this repo (no drift).
#
# Steps 1-4 + verify = the canonical staging step (C11). Step 5 = the build (C16).
#
# Usage (on Arch with archiso installed):
#   sudo ./build.sh                 # stage + build the ISO
#   ./build.sh --stage-only         # stage + verify only (no root needed)
#   ./build.sh --stage-only --releng /path/to/releng   # custom releng base
#   ./build.sh --out DIR --work DIR # choose output/work dirs
set -u

REPO="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
RELENG="${RELENG:-/usr/share/archiso/configs/releng}"
WORK=""; OUT=""; PROFILE=""; STAGE_ONLY=0

say(){ printf '%s\n' "$*"; }
die(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --releng) RELENG="$2"; shift 2 ;;
    --work)   WORK="$2";   shift 2 ;;
    --out)    OUT="$2";    shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --stage-only) STAGE_ONLY=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

: "${PROFILE:=${TMPDIR:-/tmp}/gt-profile}"
: "${WORK:=${TMPDIR:-/tmp}/gt-work}"
: "${OUT:=${TMPDIR:-/tmp}/gt-out}"

[ -d "$RELENG" ] || die "releng base not found at $RELENG (need Arch + archiso, or pass --releng)."
[ -f "$REPO/profiledef.sh" ] || die "this repo's profiledef.sh not found (run from the repo)."

# ---------- 1. copy releng base ----------
say "==> [1/4] staging releng base: $RELENG -> $PROFILE"
rm -rf "$PROFILE"; mkdir -p "$PROFILE"
cp -a "$RELENG/." "$PROFILE/"

# ---------- 2. overlay this repo (ours win) ----------
say "==> [2/4] overlaying GroundTruth OS profile (ours win on conflict)"
cp -a "$REPO/profiledef.sh" "$PROFILE/profiledef.sh"
[ -f "$REPO/pacman.conf" ] && cp -a "$REPO/pacman.conf" "$PROFILE/pacman.conf"
cp -a "$REPO/airootfs/." "$PROFILE/airootfs/"

# stamp the build's commit into the staged ISO so the installed OS has a
# self-update baseline (the dashboard compares this to GitHub; ai-os-update
# rewrites it on each update). Stamped into the staged profile only, never the
# repo (it would otherwise always be one commit stale).
BUILD_REV="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo unknown)"
printf '%s\n' "$BUILD_REV" > "$PROFILE/airootfs/usr/local/share/ai-os/INSTALLED_REV"
say "    stamped INSTALLED_REV = $BUILD_REV"

# ---------- 3. union package lists ----------
say "==> [3/4] unioning package lists"
{ grep -vhE '^\s*(#|$)' "$RELENG/packages.x86_64" "$REPO/packages.x86_64"; } \
  | sort -u > "$PROFILE/packages.x86_64"
say "    $(wc -l < "$PROFILE/packages.x86_64") packages after union"

# ---------- 4. keep releng bootloader dirs (already copied in step 1) ----------
say "==> [4/4] verifying releng bootloader dirs preserved"
for d in syslinux grub efiboot; do
  [ -e "$PROFILE/$d" ] || say "    NOTE: releng has no $d/ (ok if this releng version differs)"
done

# ---------- hash-verify: staged payload == this repo (no drift) ----------
say "==> verifying staged payload matches this repo (no drift)"
drift=0
verify_file() {  # $1 = path relative to airootfs
  local a="$REPO/airootfs/$1" b="$PROFILE/airootfs/$1"
  [ -f "$a" ] || { say "    MISSING in repo: $1"; drift=1; return; }
  [ -f "$b" ] || { say "    MISSING in staged: $1"; drift=1; return; }
  local ha hb; ha="$(sha256sum "$a" | cut -d' ' -f1)"; hb="$(sha256sum "$b" | cut -d' ' -f1)"
  if [ "$ha" = "$hb" ]; then say "    OK  $1  ($ha)"; else say "    DRIFT $1 ($ha != $hb)"; drift=1; fi
}
verify_file usr/local/share/ai-os/ai-os-dashboard.py
verify_file usr/local/bin/ai-os-install-to-disk
verify_file root/customize_airootfs.sh
verify_file etc/systemd/system/getty@tty1.service.d/autologin.conf
[ "$drift" = 0 ] || die "staged payload drifted from the repo — staging is not faithful."

# ---------- manifest (auditable record of exactly what got staged) ----------
MANIFEST="$PROFILE/staging-manifest.sha256"
( cd "$PROFILE/airootfs" && find . -type f -exec sha256sum {} + | LC_ALL=C sort ) > "$MANIFEST"
say "==> manifest: $MANIFEST ($(wc -l < "$MANIFEST") files)"

# assert our overlay actually won over releng (autologin = barron, not root)
if grep -q -- '--autologin barron' "$PROFILE/airootfs/etc/systemd/system/getty@tty1.service.d/autologin.conf" 2>/dev/null; then
  say "==> overlay confirmed: autologin = barron (releng root-autologin overridden)"
else
  die "overlay did NOT win: barron autologin not present in staged profile."
fi

if [ "$STAGE_ONLY" = 1 ]; then
  say ""
  say "STAGE-ONLY complete. Profile ready at: $PROFILE"
  say "To build: sudo mkarchiso -v -w '$WORK' -o '$OUT' '$PROFILE'"
  exit 0
fi

# ---------- 5. build ----------
command -v mkarchiso >/dev/null 2>&1 || die "mkarchiso not found — install archiso on an Arch system."
[ "$(id -u)" = 0 ] || die "the build step needs root: sudo ./build.sh"
say "==> [5/5] building ISO with mkarchiso (this takes a while)…"
mkdir -p "$OUT"
mkarchiso -v -w "$WORK" -o "$OUT" "$PROFILE" || die "mkarchiso failed."
say ""
say "BUILD COMPLETE. ISO(s) in: $OUT"
ls -lh "$OUT"/*.iso 2>/dev/null || true
