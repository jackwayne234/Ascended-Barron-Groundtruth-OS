# Getting Started — Ascended Barron: GroundTruth OS

A complete, beginner-friendly walkthrough: from downloading the file to using the
AI workflow. No Linux experience needed.

> ⚠️ **This is experimental software.** Please try it on a **spare computer or a
> virtual machine first** — not on your only/main machine. Installing to a disk
> **erases that disk.**

---

## 1. Download the ISO

1. Go to the **[Releases page](../../releases)**.
2. Download the latest `ascended-barron-groundtruth-os-vX.Y.Z-x86_64.iso`.
3. Download the matching **`SHA256SUMS`** file from the same release.

An "ISO" is a single file containing the whole operating system.

## 2. Verify your download (recommended)

This checks the file downloaded correctly and wasn't tampered with.

**Windows (PowerShell):**
```powershell
Get-FileHash .\ascended-barron-groundtruth-os-*.iso -Algorithm SHA256
```
Compare the printed hash to the line in `SHA256SUMS`. They must match.

**macOS / Linux:**
```sh
sha256sum -c SHA256SUMS
```
You want to see `OK` next to the ISO name.

## 3. Put it on a USB stick

You need a USB stick of **4 GB or larger**. **This erases the USB stick**, so use
an empty one.

Pick one tool:

- **Rufus** (Windows, easiest): select the ISO, select your USB, click *Start*,
  accept "Write in DD Image mode" if asked.
- **balenaEtcher** (Windows/macOS/Linux): *Flash from file* → pick the ISO → pick
  the USB → *Flash*.
- **`dd`** (macOS/Linux, advanced — double-check the device name!):
  ```sh
  sudo dd if=ascended-barron-groundtruth-os-*.iso of=/dev/sdX bs=4M status=progress conv=fsync
  ```
  Replace `/dev/sdX` with your USB device. **Getting this wrong can erase the
  wrong drive** — list devices with `lsblk` first.

## 4. Boot from the USB stick

1. Plug the USB into the target computer.
2. Turn it on and open the **boot menu** by tapping a key right away. Common keys:

   | Brand | Boot menu key |
   | --- | --- |
   | Dell | F12 |
   | HP | F9 (or Esc) |
   | Lenovo | F12 (or Enter → F12) |
   | Asus | F8 (or Esc) |
   | Acer | F12 |
   | MSI / Gigabyte | F11 |
   | Generic | F12 / F11 / Esc |

3. Choose your USB stick from the list.

### If you don't see the USB / it won't boot

- **Disable Secure Boot.** This release does **not** support Secure Boot. Enter
  your firmware setup (often **F2** or **Del** at power-on), find *Secure Boot*,
  set it to **Disabled**, save, and try again.
- Make sure "USB boot" is enabled and try both UEFI and Legacy/CSM modes.

## 5. First boot — the live system

GroundTruth OS starts straight into the **dashboard** — there's **no login and no
password**. You're trying it live; in live mode nothing is saved between reboots.

Take a look around:
- The **weather ticker**, clock, and battery/volume indicators.
- The three **sample projects** (see below).
- **Chromium** and a **terminal** are available.

> **Connecting to the internet:** use the Wi-Fi helper if you're not already
> online. Some features (browser, weather) need a connection; the AI workflow
> itself works offline once you've installed a local AI.

## 6. Use the workflow (the heart of GroundTruth OS)

1. **Create a task** — give your project a name (e.g. *"Build a simple personal
   webpage"*).
2. **Select the task**, then click **Work with AI**.
3. The system **creates a project folder**, drops in a **`ground-truth.md`** named
   for the task, and **opens a terminal inside that folder**. A banner explains
   what happened.
4. **Install your AI** (next section), start it in that folder, and tell it:
   > "Read `ground-truth.md` and follow it."

`ground-truth.md` is the project's living plan and memory — the AI reads it,
plans, asks questions, and records decisions and progress there.

### The sample projects

- **Plan a 3-day weekend trip** — *completed* example. Open its `ground-truth.md`
  to see what a finished plan looks like.
- **Build a simple personal webpage** — *fresh* task. Click **Work with AI** to
  watch the folder and `ground-truth.md` get created live.
- **Add a feature to my dashboard** — the **self-modification** demo: the OS
  improving itself through its own workflow. (Do this on an installed copy or with
  backups.)

## 7. Install an AI CLI

No AI is bundled — you choose. In the project terminal:

- **Claude Code**, or **any other AI CLI**, or a **local model** for a fully
  offline, private loop.
- Follow that tool's own install instructions, start it **in the project folder**,
  and point it at `ground-truth.md`.

## 8. Keep it: install to external drive (advanced)

The live USB is the safest way to try GroundTruth OS. If you want it to keep
your changes between boots, put it on a removable external drive (USB SSD,
portable HDD, or similar). The dashboard does not expose a button for this;
use the guarded terminal installer when you intentionally want to keep it.

Installing to an external drive is advanced and destructive: it erases the whole
target drive. Only do it on a spare machine after backing up anything important.

If you intentionally want to install it, run `sudo ai-os-install-to-disk` from
a terminal.

The installer lists your disks, refuses the USB you booted from, refuses
non-external/internal disks, and refuses any disk currently in use. It then asks
you to type the exact target disk name and `ERASE` before it writes anything.

The installed system also boots straight to the dashboard — **no login and no
password.** See the **Security model** section of the [README](../README.md): you
can add a password or encryption yourself if you want them.

---

## Troubleshooting

- **Black screen after boot:** wait a minute; on some hardware the graphics take a
  moment. If it persists, your GPU may need different drivers — this is an
  experimental release verified on limited hardware.
- **No Wi-Fi:** open the Wi-Fi helper and select your network. Wired connections
  come up automatically.
- **"Weather unavailable":** you're offline, or the weather component isn't
  reachable — harmless, the rest still works.
- **Reboot resets everything:** that's expected in live mode. To keep work, save
  it somewhere external or use the advanced install-to-disk flow on a spare
  machine.

This is a personal project shared as-is — **no support is promised**, but it's
yours to fork and change however you like.
