# Ascended Barron: GroundTruth OS

**Your AI workflow operating system.**

> ⚠️ **EXPERIMENTAL — early release.** This is a personal project, shared freely.
> It has been verified on one laptop and (during development) a VM. **Try it in a
> VM or on a spare machine first — don't run it on your only computer.**

*Ascended Barron: GroundTruth OS is an Arch-based Linux distribution with an
AI-native project workflow built in.*

---

## What it is

Start a project the same disciplined way every time: create a task and click
**Work with AI**. The system instantly creates a project folder for it, drops in
a `ground-truth.md` named for the task — a living plan the AI reads and follows
to take your project from idea to done — and opens a terminal right inside that
folder.

As you work, every step is logged with its reasoning automatically — **no setup,
written only to a local log file on your machine.** Your real work quietly
becomes high-quality training data that *you own* and can export whenever you
want to fine-tune your own AI models.

## ⭐ The headline: the OS can improve itself

Because *anything* can be a project here, your operating system can be one too.
Make a task like **"Add a feature to my dashboard,"** click **Work with AI**, and
the OS improves itself through its own workflow — a self-hosting AI loop.

> **Safety note:** do self-modification on an **installed copy** (or with
> backups), not your only machine. The live USB is fresh every boot, so a reboot
> is a natural undo if the AI breaks something.

## Screenshots

<!-- C15: real screenshots + GIF captured on the clean build go here -->
| Home | Eisenhower matrix | Work with AI |
| --- | --- | --- |
| _`docs/images/home.png` (coming)_ | _`docs/images/matrix.png` (coming)_ | _`docs/images/work-with-ai.gif` (coming)_ |

A short GIF of the full **create task → Work with AI → folder + `ground-truth.md`
→ terminal** loop will live at `docs/images/work-with-ai.gif`.

## Bring your own AI

No AI is bundled — it's a **true blank slate**. When you open a project terminal
you get a banner that walks you through it:

1. Install your AI CLI of choice (Claude Code, or any other).
2. Start it in the project folder.
3. Tell it: *"Read `ground-truth.md` and follow it."*

`ground-truth.md` guides both you and the AI through the whole project —
planning, decisions, steps, and progress.

## What's included

- The **dashboard** (tasks, the create-task → Work-with-AI loop, app launcher)
- **Weather ticker**, battery indicator, volume control
- **Chromium** and **lxterminal**
- Automatic, **local-only** action logging with reasons, plus an **export** that
  turns your work into AI fine-tuning data
- Three **sample projects** to learn from:
  - **Plan a 3-day weekend trip** — a *completed* example (filled `ground-truth.md`)
  - **Build a simple personal webpage** — a *fresh* task to start live
  - **Add a feature to my dashboard** — the self-modification demo
- A tiny **sample training-data export** so you can see the format

## Try it / install

1. **Download** the ISO from [Releases](../../releases).
2. **Verify** it with the published `SHA256SUMS` (see the
   [Getting Started guide](docs/GETTING-STARTED.md)).
3. **Flash** it to a USB stick (Rufus, balenaEtcher, or `dd`).
4. **Boot** it — it comes up live so you can try it instantly. To keep it, use the
   **💾 Install to disk** button.

Full step-by-step instructions (including BIOS/boot keys and Secure Boot) are in
the **[Getting Started guide](docs/GETTING-STARTED.md)**.

### Boot compatibility

Boots on **UEFI** (x64 + ia32) and **legacy BIOS**. **Secure Boot is not supported
in v1** — turn it off in your firmware if it's on.

## Updating

Updating is one click: open **Update OS** in the dashboard's Apps grid (or in
**Settings**). It pulls the latest **published release**, backs up the current
files first, and replaces only the OS's own app files — your projects and data in
`~/workspace` are never touched. The Update OS tile turns **amber** (with a
dismissible banner) when a newer version is available.

From **v1.1.0** the update system also:

- installs the latest **published release** (a git tag) rather than the moving
  branch tip, so you only run versions the project actually cut;
- shows your **current version** in the bottom bar and **Settings**;
- lets you **undo the last update** and **turn the update check off** in Settings.

### Older installs (v1.0.0 / v1.0.1)

These predate the updater. Add it once and the **Update OS** button takes over:

```
curl -fsSL https://raw.githubusercontent.com/jackwayne234/Ascended-Barron-Groundtruth-OS/main/groundtruth-os/bootstrap-updater.sh | bash
```

Prefer not to pipe to a shell? Do the same thing by hand:

```
git clone --depth 1 https://github.com/jackwayne234/Ascended-Barron-Groundtruth-OS.git /tmp/abgt \
  && sudo install -m755 /tmp/abgt/groundtruth-os/airootfs/usr/local/bin/ai-os-update /usr/local/bin/ \
  && sudo install -d /usr/local/share/ai-os \
  && ai-os-update
```

## Security model — please read

This is a **single-user, open** system by design:

- It **boots straight to the dashboard — no login and no password.** Anyone with
  physical access to the machine can use it.
- Administrative actions don't prompt for a password either.
- The disk is **not encrypted.** If the machine is lost or stolen, its files can
  be read.

This keeps it simple and friendly to try. If you want a login, a password, or
disk encryption, you can add them yourself — or fork it and build a multi-user
version (the MIT license lets you).

## A note on privacy

GroundTruth OS's own logging writes only to a local file — it never uploads your
data. Keep in mind that if you connect a **cloud AI provider** (Claude, OpenAI,
etc.), that provider will log your prompts on their side according to their own
policies, exactly as they always do. That's separate from GroundTruth OS and
outside our control. Want zero third-party logging? **Use a local model** — then
the whole loop is fully in-house: the model runs locally, the logs write locally,
and nothing leaves your machine.

For full transparency, the OS itself makes **one** small outbound request: on
startup it asks this GitHub repo "what's the latest version?" so the **Update OS**
tile can tell you when an update exists. It's a version check only — it sends
none of your data. (And of course, downloading an update contacts GitHub too,
when you click Update.)

## Build it yourself

The whole thing is open. This repo is a rebuildable **archiso profile** — see
**[BUILD.md](BUILD.md)**. On an Arch system with `archiso`:

```sh
sudo ./build.sh
```

## License & credits

Original code (dashboard, scripts, branding) is **MIT licensed** — see
[LICENSE](LICENSE). Bundled third-party components (Arch Linux, the Linux kernel,
Chromium, lxterminal, and others) keep their own licenses; see
[NOTICE](NOTICE.md).

Created by **Christopher Riner** ([@jackwayne234](https://github.com/jackwayne234)).

## Project status

A personal project, shared freely under MIT — **fork it and make it your own.**
To keep maintenance at zero:

- **Pull Requests are off** — no outside code is merged.
- **Issues are off** — no inbox, no feature requests, no support promised.

You're free to take it in any direction you like.
