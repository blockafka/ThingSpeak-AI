---
name: xhs-content-collector
description: Archive Xiaohongshu image-text notes for home interior/custom design research from profile URLs, note URLs, or task JSON. Use only when the user explicitly asks to collect Xiaohongshu content, save note body text and original images, skip video notes, or run the packaged collector.
argument-hint: "<task-json | profile/note urls>"
disable-model-invocation: true
---

# Xiaohongshu Content Collector

Run this skill only after the user invokes `/xhs-content-collector` or otherwise explicitly asks to collect Xiaohongshu materials. Treat collection as a side-effecting browser automation task.

## Required Precondition

Read `references/auth-login-state.md` before planning login, customer handoff, cloud execution, or expired-session handling.

Require a valid Xiaohongshu Playwright `storage_state.json` before collection. Prefer the path in `XHS_STORAGE_STATE_PATH`; otherwise use `data/xhs/auth/storage_state.json` in the current project. If the state file is missing or stale, stop and ask for a human login refresh. Do not collect anonymously.

## Run Full Note Archive

Read `references/task-schema.md` before creating or modifying a task JSON.

If `$ARGUMENTS` points to an existing JSON file, use that as the task. If `$ARGUMENTS` contains note or profile URLs, create a local runtime task JSON with those values and keep it out of commits.

From the project root, run:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/xhs_full_note_collect.py \
  --task <task-json> \
  --output "${XHS_OUTPUT_ROOT:-data/xhs_collected}" \
  --storage-state "${XHS_STORAGE_STATE_PATH:-data/xhs/auth/storage_state.json}" \
  --headless
```

On Windows PowerShell, use the same script path and set defaults explicitly:

```powershell
$outputRoot = if ($env:XHS_OUTPUT_ROOT) { $env:XHS_OUTPUT_ROOT } else { "data/xhs_collected" }
$storageState = if ($env:XHS_STORAGE_STATE_PATH) { $env:XHS_STORAGE_STATE_PATH } else { "data/xhs/auth/storage_state.json" }

python "${CLAUDE_SKILL_DIR}\scripts\xhs_full_note_collect.py" `
  --task <task-json> `
  --output $outputRoot `
  --storage-state $storageState `
  --headless
```

## Output Contract

Archive each successful image-text note as:

```text
<output>/<blogger>/<YYYY-MM-DD>_<title>/
├── body.txt
├── metadata.json
├── image_urls.txt
├── full_text_snapshot.txt
├── 采集状态.txt
└── images/
```

Treat a note as successful only when note ID, source URL, non-empty body/snapshot, metadata, image URL list, status file, and downloaded images are present and internally consistent.

## Selection Rules

- Collect only image-text notes.
- Skip video notes and video copy.
- For home/custom/interior design ranking, sort by industry match, collect count, like count, comment count, image-text status, then publish time.
- Keep schedules conservative. For recurring jobs, read `references/hermes-cloud.md`.

## Safety Rules

- Do not collect passwords, OTPs, captcha answers, raw cookies, or account secrets.
- Do not bypass Xiaohongshu anti-bot, signature, or security verification.
- Treat `storage_state.json` as a secret and never include it in prompts, logs, git commits, or archives.
- Stop with a clear status when login, captcha, or security verification is required.
