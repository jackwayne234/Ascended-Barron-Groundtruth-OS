#!/usr/bin/env bash
# Runs once inside the airootfs chroot during `mkarchiso` (archiso convention).
# Sets up the live system: locale, the non-root live user, autologin target,
# services, and sudo. No personal data, no bundled agent, no root desktop.
set -e -u

# --- locale ---
sed -i 's/#\(en_US\.UTF-8 UTF-8\)/\1/' /etc/locale.gen
locale-gen
ln -sf /usr/share/zoneinfo/UTC /etc/localtime

# --- root: usable shell, but no autologin/desktop as root (C5) ---
usermod -s /usr/bin/bash root

# --- the single user `barron` (non-root) — Q1/Q2/Q3 (locked 2026-06-14) ---
# uid/gid 1000, in wheel; NO password. This same account is used on BOTH the
# live image and an installed system: the installer just copies this system to
# disk, so the installed machine also boots straight in as `barron` with no
# login and no password (the locked "no login at all" decision).
if ! id barron >/dev/null 2>&1; then
  useradd -m -u 1000 -U -G wheel -s /usr/bin/bash barron
fi
passwd -d barron          # passwordless: boots straight to the dashboard
chown -R barron:barron /home/barron

# --- sudo for wheel (live convenience; user has no password so NOPASSWD is
#     required for sudo to function at all on the live image) ---
install -d -m 750 /etc/sudoers.d
echo '%wheel ALL=(ALL:ALL) NOPASSWD: ALL' > /etc/sudoers.d/10-wheel-nopasswd
chmod 440 /etc/sudoers.d/10-wheel-nopasswd

# --- services: NetworkManager owns the network; drop releng's defaults ---
# (releng enables systemd-networkd/resolved via airootfs symlinks; we use NM and
#  we do NOT auto-run sshd on a public live image — C5.)
systemctl disable systemd-networkd.service systemd-resolved.service 2>/dev/null || true
systemctl disable sshd.service 2>/dev/null || true
systemctl enable NetworkManager.service
# We start X from tty1 via getty autologin + ~/.bash_profile (startx), so the
# default target is multi-user; the getty drop-in (shipped in airootfs) autologins.
systemctl set-default multi-user.target

# --- ensure our helper CLIs are executable in the shipped image ---
# (profiledef file_permissions did not reliably set the exec bit on a real
# build, so set it here in the chroot where it's guaranteed to stick.)
chmod 0755 /usr/local/bin/ai-os-* /usr/local/bin/start-ai-os-gui-dashboard 2>/dev/null || true

# NOTE: do NOT delete this script here — mkarchiso removes customize_airootfs.sh
# from the image itself after running it. Self-deleting makes mkarchiso's own
# cleanup `rm` fail and aborts the build.
