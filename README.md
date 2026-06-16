# Ascended Barron: GroundTruth OS

An Arch-based live environment for AI-assisted work, with local workflow logging built in.

This project is experimental and personal, but it is real and usable. Boot it from removable media, open the dashboard, create a task, and start working with your AI tool of choice. As you work, the system records your workflow to a local training log that stays on your machine.

No AI model is bundled. GroundTruth OS gives you the structure, workspace, and local logging. You bring the AI.

## What it does

GroundTruth OS turns each task into a project workspace.

When you create a task and open its project terminal, the system:

1. creates a folder for that task,
2. drops in a `ground-truth.md` file,
3. opens a terminal in that folder, and
4. leaves the rest to you and your AI tool.

The idea is simple: start work the same way every time, keep the project organized, and keep a local record of what happened while you worked.

## The core idea

This OS is built around one workflow:

create a task -> open the project terminal -> start your AI in that folder -> tell it to read `ground-truth.md`

Because anything can be a task, the OS itself can be one too. You can create a task like `Add a feature to my dashboard`, open the project terminal, and use the same workflow to improve the system from inside itself.

If you do that, use an installed copy or keep backups. A live boot is easy to throw away on reboot. A modified install is not.

## Bring your own AI

GroundTruth OS does not ship with Claude Code, Codex, or any other assistant preinstalled.

You choose what to run:

- a cloud AI CLI,
- a local model,
- or any other terminal-based AI workflow you prefer.

The intended flow is:

1. boot the OS,
2. open a project terminal,
3. install or start your AI tool there,
4. tell it: `Read ground-truth.md and follow it.`

If you want a fully local loop, use a local model. If you use a cloud provider, that provider will still handle your prompts under its own policies.

## What is included

The release includes:

- the dashboard,
- task management and the project-terminal workflow,
- Chromium,
- lxterminal,
- weather, battery, volume, and network helpers,
- local workflow logging and export helpers,
- sample projects,
- and a sample training-data export.

Sample projects currently included:

- `Plan a 3-day weekend trip` - a completed example
- `Build a simple personal webpage` - a fresh task to try live
- `Add a feature to my dashboard` - the self-modification demo

## Local logging

GroundTruth OS writes its own workflow log to local files on your machine.

That log is meant to capture your work session in a training-friendly format that you can inspect, keep, export, or use later however you want. The OS does not upload that data.

This is separate from any cloud AI provider you choose to use. If you connect to a hosted model, that provider may still retain prompts or usage data under its own policies. GroundTruth OS cannot change that.

If you want the whole loop to stay local, run a local model.

## How to boot it

1. Download the latest ISO from [Releases](../../releases).
2. Verify it with the published `SHA256SUMS` file.
3. Write the ISO to removable media with a tool like Rufus, balenaEtcher, or `dd`.
4. Boot your computer from that media.

Full step-by-step instructions are in [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md).

## Removable-media workflow

The main experience is a live boot from removable media.

You can try the system without touching your internal disk. If you want to keep a portable copy on an external drive, the repo also includes an advanced terminal installer:

`sudo ai-os-install-to-disk`

That path is intentionally kept out of the casual dashboard UI. Read the getting-started guide and use caution before writing to any disk.

## Boot compatibility

GroundTruth OS currently boots on:

- UEFI x64
- UEFI ia32
- legacy BIOS

Secure Boot is not supported in v1. If Secure Boot is enabled, turn it off in firmware before booting.

## Updating

GroundTruth OS includes an updater.

From the dashboard you can:

- check for updates,
- install the latest published release,
- see the current version,
- and undo the last update.

Updates replace the OS app files only. Your work in `~/workspace` is not touched by the updater.

Older installs from before the updater can bootstrap it with:

```sh
curl -fsSL https://raw.githubusercontent.com/jackwayne234/Ascended-Barron-Groundtruth-OS/main/bootstrap-updater.sh | bash
```

If you do not want to pipe to a shell, the README in older versions also shows the manual install steps.

## Security model

Read this section before using the OS on real hardware.

GroundTruth OS is intentionally simple and intentionally open:

- it boots straight to the dashboard,
- there is no login prompt,
- there is no password by default,
- administrative actions are not protected by a normal multi-user desktop security model,
- and the disk is not encrypted by default.

This makes the system easy to boot and easy to understand, but it also means anyone with physical access to the machine can access the system.

If you want passwords, encryption, or a different trust model, you will need to add them yourself or fork the project.

## Privacy note

GroundTruth OS itself keeps its workflow logging local.

It does make one small outbound request on startup to check the latest published version so the updater can tell you when an update exists. Downloading updates also contacts GitHub, of course.

Outside of that, your privacy mainly depends on which AI tool you connect to the system.

## Build it yourself

This repository is an `archiso` profile overlay.

If you have an Arch build environment with `archiso` installed:

```sh
sudo ./build.sh
```

For build details, see [BUILD.md](BUILD.md).

## License and credits

Original project code in this repository is MIT licensed. See [LICENSE](LICENSE).

Bundled third-party components keep their own licenses. See [NOTICE](NOTICE.md).

Created by Christopher Riner ([@jackwayne234](https://github.com/jackwayne234)).

## Project status

This is a personal project released publicly under MIT.

It is meant to be used, studied, and forked. It is not presented as a polished mainstream distro, a managed support product, or a multi-contributor project.

Current maintenance stance:

- Issues are off.
- Pull requests are off.
- No support is promised.

If the project is useful to you, fork it and make it your own.
