#!/usr/bin/env bash
# generate-release-key.sh — create the dedicated GroundTruth OS release signing
# key (maintainer-only; run this on YOUR machine, never in CI/cloud).
#
# Implements the locked key decisions:
#   - dedicated release key, project identity + alias email   (Q26/Q36)
#   - 2-year expiry, renewable                                (Q37)
#   - exports an encrypted private-key backup + a revocation
#     certificate for safe offline storage                    (Q38)
#   - writes the PUBLIC key to the OS tree so it ships baked-in (Q52)
#
# It NEVER commits the private key. Only the public key (release-pubkey.asc)
# belongs in the repo.
set -euo pipefail

NAME="${REL_KEY_NAME:-Ascended Barron Releases}"
EMAIL="${REL_KEY_EMAIL:-chrisriner45+releases@gmail.com}"
EXPIRE="${REL_KEY_EXPIRE:-2y}"

REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
PUBKEY_DEST="$REPO/airootfs/usr/local/share/ai-os/release-pubkey.asc"
BACKUP_DIR="${REL_KEY_BACKUP_DIR:-$HOME/ascended-barron-release-key-backup}"

say(){ printf '%s\n' "$*"; }
command -v gpg >/dev/null 2>&1 || { echo "ERROR: gpg not installed." >&2; exit 1; }

say "This will generate the release signing key:"
say "  Name:   $NAME"
say "  Email:  $EMAIL"
say "  Expiry: $EXPIRE (renewable)"
say "  Public key -> $PUBKEY_DEST"
say "  Encrypted backup + revocation cert -> $BACKUP_DIR"
say ""
read -rp "Proceed? Type 'yes': " ans
[ "$ans" = "yes" ] || { say "Cancelled."; exit 0; }

# Generate (gpg will prompt for a passphrase — choose a strong, unique one).
gpg --quick-generate-key "$NAME <$EMAIL>" ed25519 sign "$EXPIRE"

FPR="$(gpg --list-keys --with-colons "$EMAIL" | awk -F: '/^fpr:/{print $10; exit}')"
[ -n "$FPR" ] || { echo "ERROR: couldn't determine the new key fingerprint." >&2; exit 1; }
say ""
say "Key fingerprint: $FPR"

# Public key into the OS tree (replaces the PLACEHOLDER), so it ships baked-in.
gpg --armor --export "$FPR" > "$PUBKEY_DEST"
say "Wrote public key -> $PUBKEY_DEST"

# Encrypted offline backup of the PRIVATE key + a revocation certificate (Q38).
mkdir -p "$BACKUP_DIR"; chmod 700 "$BACKUP_DIR"
gpg --armor --export-secret-keys "$FPR" > "$BACKUP_DIR/release-private-key.asc"
# GnuPG 2.1+ auto-writes a revocation certificate at key-generation time; copy
# that (reliable). Fall back to generating one non-interactively if it's absent.
AUTO_REVOC="${GNUPGHOME:-$HOME/.gnupg}/openpgp-revocs.d/$FPR.rev"
if [ -f "$AUTO_REVOC" ]; then
  cp "$AUTO_REVOC" "$BACKUP_DIR/release-revocation.asc"
else
  printf 'y\n0\n\ny\n' | gpg --command-fd 0 --status-fd 2 --pinentry-mode loopback \
    --output "$BACKUP_DIR/release-revocation.asc" --gen-revoke "$FPR" 2>/dev/null || true
fi
chmod 600 "$BACKUP_DIR"/*.asc 2>/dev/null || true

say ""
say "✓ Done."
say ""
say "NEXT (do these yourself — they are deliberately not automated):"
say "  1. Move $BACKUP_DIR to ENCRYPTED OFFLINE storage (USB in a drawer /"
say "     password manager). The private key must NOT stay loose on disk and"
say "     must NEVER be committed."
say "  2. Record the fingerprint in the repo/release notes so users can confirm"
say "     it:  $FPR"
say "  3. Commit ONLY the public key:"
say "       git add airootfs/usr/local/share/ai-os/release-pubkey.asc"
say "  4. Set REL_KEY_FPR=$FPR when running tools/make-release.sh so it signs"
say "     with this key."
