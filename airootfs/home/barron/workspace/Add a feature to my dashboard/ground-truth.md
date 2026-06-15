# Add a feature to my dashboard — Ground Truth

> SAMPLE PROJECT (C) — the headline trick: **GroundTruth OS can improve
> itself.** Because the dashboard is just code on this machine, "add a feature
> to it" is a normal project: make a task, press **Work with AI**, and the AI
> edits the live system through the same workflow you use for anything else.
> This sample is teed up for you — read it, then continue it with your own AI.

> ⚠️ **SAFETY NOTE — read before you let an AI change a running system.**
> Modifying the OS you are currently using can break it. Do self-modification
> on an **installed copy** (not your only computer), and keep a backup. The
> live USB is a natural safety net: it is **fresh every boot**, so if a change
> breaks something, just reboot and you are back to a clean slate. Prefer
> testing changes before making them permanent.

## Purpose of This File

A `ground-truth.md` file is the project’s source of truth. It tells the AI what the project is, what decisions have been made, what still needs to be asked, and whether the AI has permission to start working — so it doesn't guess, restart, or build before you've approved the direction.

## AI Start Instructions

When the AI works in this folder, it should read this file first and:

1. Confirm the desired outcome below with the user (or refine it).
2. Ask any planning questions one at a time, with short options and a recommendation.
3. Record questions, answers, and locked decisions back into this file.
4. Break the work into small chunks and record them here.
5. Ask: **“Do I have your permission to start working from this ground truth and chunk plan?”**
6. Do **not** edit the live dashboard until permission is granted — and follow the safety note above.
7. Log progress in the Progress Log.

## Desired Outcome

**Drafted (confirm with the user).** Add one small, useful feature to the AI OS
dashboard — for example a live clock in the top bar, or a button that opens a
chosen folder. The point is to demonstrate the OS improving itself through its
own task → Work with AI → ground-truth workflow.

The dashboard lives at: `/usr/local/share/ai-os/ai-os-dashboard.py`
(it is a single Python/tkinter file). On an installed system you'd edit it,
restart the dashboard, and see your change.

## Planning Status

- Desired outcome: **Drafted — confirm/adjust with the user.**
- Planning pass: **Not started** (ask the questions below one at a time).
- Chunk plan: **Not created yet.**
- Permission to start work: **Not granted yet.**

## Planning Q&A Ledger

### Desired Outcome Question

**Question:** What do you want the desired outcome of this project to be?
**User answer:** _To be confirmed — the draft above is a starting point._
**Locked decision:** _Not locked yet._

_(Suggested first planning questions for the AI to ask: Which single feature?
Where on the dashboard should it appear? Test on an installed copy or a live
session? Should the change be permanent or just tried this session?)_

## Permission to Start

_Not granted yet. The AI should confirm the feature and the plan, honor the
safety note, then ask: “Do I have your permission to start working from this
ground truth and chunk plan?”_

## Progress Log

### 2026-06-14
- Shipped as a teed-up sample to demonstrate the self-modifying-OS workflow.
- Desired outcome drafted; planning questions and permission still pending so a
  new user can drive the rest with their own AI.
