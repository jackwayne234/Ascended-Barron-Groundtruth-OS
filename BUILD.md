# Building Ascended Barron: GroundTruth OS

This repo is an **archiso profile overlay**. It contains everything unique to
GroundTruth OS (the dashboard, helper CLIs, session config, samples, package
additions, and `profiledef.sh`) and builds on top of Arch's official `releng`
profile for the parts that must stay version-matched to your archiso (the
bootloader configs and the base live-boot package set).

You need a machine (or VM) running **Arch Linux with `archiso` installed**
(`mkarchiso`). The Ubuntu host this was developed on cannot run `mkarchiso`
natively — the project uses a dedicated Arch builder VM for this.

## Build contract (what the staging step does)

Assemble a build profile, then run `mkarchiso`:

1. Start from the version-matched releng base:
   `cp -a /usr/share/archiso/configs/releng /tmp/gt-profile`
2. Overlay this repo's profile files (ours win on conflicts):
   - `profiledef.sh`            → replaces releng's
   - `pacman.conf`              → replaces releng's
   - `airootfs/`                → overlaid on top of releng's airootfs
     (our `getty@tty1` autologin drop-in, `~user` session files, dashboard,
     helpers, samples, `customize_airootfs.sh`, hostname all win)
3. Union the package lists so no live-boot essential is dropped:
   `sort -u releng/packages.x86_64 + this repo's packages.x86_64`
   → `/tmp/gt-profile/packages.x86_64`
4. Keep releng's `syslinux/`, `grub/`, `efiboot/` bootloader dirs (they are
   referenced by our `bootmodes` and are correct for UEFI x64/ia32 + BIOS).
5. Build:
   `mkarchiso -v -w /tmp/gt-work -o /tmp/gt-out /tmp/gt-profile`

All five steps are automated by **`./build.sh`** in this repo:

```sh
sudo ./build.sh            # stage + build the ISO (needs Arch + archiso + root)
./build.sh --stage-only    # stage + verify only, no root (inspect the profile)
```

`build.sh` runs steps 1–4, **hash-verifies** that the staged payload matches
this repo (fails on any drift), writes a `staging-manifest.sha256`, confirms our
overlay won (autologin = `barron`, not releng's root), then runs `mkarchiso`
(step 5). The overlay order matters: **releng first, this repo second**, so our
autologin/user/session files replace releng's root-autologin.

## What this profile sets up

- **Single user `barron`** (non-root, uid 1000, in `wheel`, no password) with
  autologin on tty1; `~/.bash_profile` runs `startx`, `~/.xinitrc` launches the
  dashboard. This same account is used live AND when installed on a removable
  external drive, so the installed machine also boots straight to the dashboard
  — no login, no password (the installer just copies this system to the target
  drive; see C10 / `ai-os-install-to-disk`).
- **NetworkManager** enabled at boot; releng's systemd-networkd/resolved and
  sshd are disabled (no auto-SSH on a public image).
- **Hostname** `groundtruth-os`, locale `en_US.UTF-8`, timezone UTC.
- The dashboard, helper CLIs, the `ai_big_log` logging/export library, the
  shipped sample content under `/home/barron`, and the sample export example.

## Boot compatibility

UEFI (x64 + ia32) and legacy BIOS (Q11). **Secure Boot is not supported in v1** —
disable it in firmware if your machine has it on.
