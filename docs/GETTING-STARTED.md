# Getting Started — Ascended Barron: GroundTruth OS

A beginner-friendly walkthrough for downloading the ISO, booting the system, and using the AI workflow.

> This is experimental software. Use a spare computer if you can. If you write the image to removable media, that media will be erased.

## 1. Download the ISO

1. Open the [Releases page](../../releases).
2. Download the latest `ascended-barron-groundtruth-os-vX.Y.Z-x86_64.iso`.
3. Download the matching `SHA256SUMS` file from the same release.

An ISO is a single file containing the whole live system.

### Verify the download

Verifying the ISO makes sure the file downloaded correctly and matches the published checksum.

Windows PowerShell:

```powershell
Get-FileHash .\ascended-barron-groundtruth-os-*.iso -Algorithm SHA256
```

Compare the printed hash to the matching line in `SHA256SUMS`.

macOS or Linux:

```sh
sha256sum -c SHA256SUMS
```

You want to see `OK` next to the ISO filename.

## 2. Write it to removable media

Use a USB stick or external drive with at least 4 GB of space. Writing the ISO will erase that device.

Common options:

- Rufus on Windows: choose the ISO, choose the USB device, and start the write. If Rufus asks, use DD Image mode.
- balenaEtcher on Windows, macOS, or Linux: select the ISO, select the target device, and flash it.
- `dd` on macOS or Linux if you are comfortable working from the terminal.

Example `dd` command:

```sh
sudo dd if=ascended-barron-groundtruth-os-*.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

Replace `/dev/sdX` with the correct device. Double-check before you run it. Using the wrong device can erase the wrong disk.

## 3. Boot from the device

1. Plug the prepared device into the computer.
2. Turn the computer on and open the boot menu right away.
3. Select the USB stick or external drive from the list.

Common boot-menu keys:

| Brand | Boot menu key |
| --- | --- |
| Dell | F12 |
| HP | F9 or Esc |
| Lenovo | F12 or Enter, then F12 |
| Asus | F8 or Esc |
| Acer | F12 |
| MSI / Gigabyte | F11 |
| Generic | F12, F11, or Esc |

### If the device does not appear or will not boot

- Disable Secure Boot. GroundTruth OS v1 does not support Secure Boot.
- Make sure USB boot is enabled in firmware.
- If your machine offers both UEFI and Legacy/CSM modes, try the other one.

## 4. First boot

GroundTruth OS boots straight into the dashboard. There is no login screen and no password prompt by default.

The normal experience is a live boot from removable media, so you can try the system without touching your internal disk.

Once the desktop appears, you can:

- look through the sample projects,
- open Chromium,
- open a terminal,
- connect to Wi-Fi if needed,
- and start a new task.

If you are offline, some parts of the interface such as the browser, weather, and update check will not work. The core project workflow can still work offline once you install a local AI tool.

## 5. Start a task

This is the main workflow of the OS.

1. Create a task and give it a name.
2. Select that task in the dashboard.
3. Open the project terminal for it.

When you do that, GroundTruth OS:

1. creates a folder for the task,
2. drops in a `ground-truth.md` file,
3. opens a terminal in that folder,
4. and leaves the rest to you and your AI tool.

The point is to start every project the same way: one folder, one project prompt file, one terminal in the right place.

## 6. Start your AI tool

No AI tool is bundled with the OS. You choose what to run.

In the project terminal, install or start the AI tool you want to use. That can be a cloud AI CLI, a local model, or another terminal-based assistant.

Then tell it:

`Read ground-truth.md and follow it.`

That file is the starting point for the project. It gives the AI a place to read the task, capture decisions, and keep the work organized as the project grows.

## 7. Understand the logging model

GroundTruth OS writes its own workflow log to local files on your machine.

That logging is part of GroundTruth OS itself. It is separate from any cloud provider you choose to use.

If you connect to a hosted AI service, that provider may still retain prompts or usage data under its own policies. If you want the whole loop to stay local, use a local model.

## 8. Sample projects

The release includes a few sample projects so you can see the workflow immediately:

- `Plan a 3-day weekend trip` — a completed example
- `Build a simple personal webpage` — a fresh task to try live
- `Add a feature to my dashboard` — the self-modification demo

If you try the self-modification path, do it on an installed copy or keep backups. A live boot is easy to discard on reboot. A modified install is not.

## 9. Optional external-drive install path

The main experience is the live boot from removable media.

If you want to keep a portable copy on an external drive, the repo also includes an advanced terminal installer:

```sh
sudo ai-os-install-to-disk
```

Use that carefully. It writes to a target disk and is intentionally not presented as a casual dashboard button.

## 10. Updating

GroundTruth OS includes an updater.

From the dashboard, you can:

- check for updates,
- install the latest published release,
- see the current version,
- and undo the last update.

The updater replaces the OS app files only. Your work in `~/workspace` is not touched by the updater.

Older installs from before the updater can bootstrap it with:

```sh
curl -fsSL https://raw.githubusercontent.com/jackwayne234/Ascended-Barron-Groundtruth-OS/main/bootstrap-updater.sh | bash
```

## Troubleshooting

Black screen after boot:
- Wait a minute first. Some hardware takes a little longer to bring up graphics.
- If it stays black, your system may need different graphics support than this release currently provides.

No Wi-Fi:
- Open the Wi-Fi helper and connect manually.
- Wired networking should come up automatically on most machines.

Weather unavailable:
- You are probably offline, or the weather source is unreachable.
- The rest of the system can still work.

## Security note

GroundTruth OS is intentionally simple and intentionally open.

- It boots straight to the dashboard.
- There is no login prompt by default.
- There is no password by default.
- The disk is not encrypted by default.

That makes it easy to boot and easy to understand, but it also means anyone with physical access to the machine can access the system.

If you want a different trust model, you will need to add it yourself or fork the project.

## Need more detail?

For the product overview, privacy note, and build instructions, see the [README](../README.md).

This is a personal project released publicly under MIT. No support is promised, but you are free to fork it and make it your own.
