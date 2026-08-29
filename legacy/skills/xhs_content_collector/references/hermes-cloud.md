# Hermes Cloud Deployment

## Architecture

Run the collector as a Hermes skill-backed job:

1. A scheduler emits a JSON task payload.
2. Hermes calls the model API with the task and `$xhs-content-collector`.
3. The model selects a deterministic command.
4. The Hermes worker runs the script in a container with Python, Playwright, and Chromium.
5. Output folders are persisted to object storage or a mounted volume.
6. The job returns the summary JSON path and key counts.

## Container Requirements

- Python 3.10+.
- `playwright` Python package.
- Browser binaries installed with `python -m playwright install chromium`.
- Writable artifact directory, for example `/data/xhs_collected`.
- Secret path for Xiaohongshu login state, for example `/run/secrets/xhs_storage_state.json`.

## Environment Variables

- `OPENAI_API_KEY`: Model API key used by Hermes, not by the collector script itself.
- `XHS_STORAGE_STATE_PATH`: Path to saved Playwright storage state.
- `XHS_OUTPUT_ROOT`: Artifact output root.
- `HERMES_RUN_ID`: Optional run identifier for logs and summaries.
- `TZ`: Use `Asia/Shanghai` for date-based folder names.

## Scheduled Job Example

```json
{
  "name": "xhs-designers-daily",
  "cron": "0 9 * * *",
  "timezone": "Asia/Shanghai",
  "skill": "xhs-content-collector",
  "command": [
    "python",
    "hermes/skills/xhs-content-collector/scripts/xhs_full_note_collect.py",
    "--task",
    "hermes/tasks/xhs_designers_daily.json",
    "--output",
    "${XHS_OUTPUT_ROOT}",
    "--storage-state",
    "${XHS_STORAGE_STATE_PATH}",
    "--headless"
  ]
}
```

## Login State Refresh

Do not put passwords in Hermes. Refresh login manually:

1. Run an official Xiaohongshu browser login flow in a secure environment.
2. Save Playwright `storage_state.json`.
3. Upload it to a secret manager or encrypted volume.
4. Rotate it when the job reports `login_required`, `security_verification`, or `captcha_required`.

## Failure Handling

- `no_new_note`: Profile has no new image-text note beyond existing metadata.
- `login_required`: Saved login state is expired.
- `security_verification`: Xiaohongshu shows verification. Stop and refresh manually.
- `detail_unavailable`: Note is deleted, private, or returns 404.
- `download_partial`: Metadata saved, but one or more images failed to download.

