# Getting Started — Ascended Barron: GroundTruth OS

A complete, beginner-friendly walkthrough: from downloading the file to using the
AI workflow. No Linux experience needed.

> ⚠️ **This is experimental software.** Please try it on a **spare computer or a
> virtual machine first** — not on your only/main machine. Installing to an external
> Hard Drive erases that external hard drive.

---

## 1. Download the ISO

1. Go to the **[Releases page](../../releases)**.
2. Download the latest `ascended-barron-groundtruth-os-vX.Y.Z-x86_64.iso`.

   ## Optional additional security
  
Download the matching **`SHA256SUMS`** file from the same release.

An "ISO" is a single file containing the whole operating system.

Verify your download (recommended)

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

## Resuming regular installation instruction here

## 2. Put it on a USB stick

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

## 3. Boot from the USB stick

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

## 4. First boot

ABG-OS starts straight into the **dashboard** — there's **no login and no
password**. It's a persistent OS on an external thumbdrive. When you're done
you can shutdown and remove the disk and store it in a safe location, or take
it with you to use in another computer without having to carry around a whole
other computer.

Take a look around:
- The **weather ticker**, clock, and battery/volume indicators. I love the weather
  channel. This is a nod to the 90's weather channel. When it was good.
- Click on the sample projects to take a look. Or start a task, select it, open in
  terminal button, install your desired AI (local LLM or cloud)
  
  **If you use a cloud AI provider, the cloud provider will still do their normal
  logging that they do. But now, your local logs will fill up as you work too so
  you can train or fine tune your OWN LLM that compliments how YOU work. Choose a
  local LLM if you don't want a cloud provider to harvets your information as you
  work.**
  
- **Chromium** and a **terminal** are available.

> **Connecting to the internet:** use the Wi-Fi helper if you're not already
> online. Some features (browser, weather) need a connection; the AI workflow
> itself works offline once you've installed a local AI.

## 5. Use the workflow (the heart of GroundTruth OS)

1. **Create a task** — give your project a name (e.g. *"Build a simple personal
   webpage"*).
2. **Select the task**, then click **Open Project Terminal**.
3. The system **creates a project folder**, drops in a **`ground-truth.md`** named
   for the task, and **opens a terminal inside that folder**. A banner explains
   what happened.
4. **Install your AI** (next section), start it in that folder, and tell it:
   > "Read `ground-truth.md` and follow it."

**`ground-truth.md` is the project's scaffolding for the AI — the AI reads it,
Asks your desired outcome of the project, asks 25 questions about the project
mulitple choice with it's recommendation for each question one at a time, and
records decisions and progress there. Then the AI will reference the ground-truth.md
file while working on the project. It divides projects into chunks with their own
files and logs appropriate information in each chunk of the project. AI works best
an organized scaffolding. That's what this operating system does automatically,
and creates training data stored locally as you work. You don't have to mess with
it.**

### The sample projects

- **Build a simple personal webpage** — *fresh* task. Click **Work with AI** to
  watch the folder and `ground-truth.md` get created live.
- **Add a feature to my dashboard** — the **self-modification** demo: the OS
  improving itself through its own workflow. (Do this on an installed copy or with
  backups.)

## 6. Install an AI CLI

No AI is bundled — you choose. In the project terminal:

- **Claude Code**, or **any other AI CLI**, or a **local model** for a fully
  offline, private loop.
- Follow that tool's own install instructions, start it **in the project folder**,
  and point it at `ground-truth.md`.

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
  
## Create a task to modify or troubleshoot your system. It's completely yours

- **"Weather unavailable":** you're offline, or the weather component isn't
  reachable — harmless, the rest still works. Or, create a task and use AI to fix
  it.

This is a personal project shared as-is — **no support is promised**, but it's
yours to fork and change however you like.
