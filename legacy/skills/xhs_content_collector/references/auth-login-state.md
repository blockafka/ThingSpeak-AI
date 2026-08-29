# Login State Strategy

Xiaohongshu login is the fragile part of this workflow. Keep authentication separate from collection.

## Contract

The collector consumes an existing Playwright `storage_state.json`:

```bash
python <skill-dir>/scripts/xhs_full_note_collect.py \
  --task <task-json> \
  --output "${XHS_OUTPUT_ROOT}" \
  --storage-state "${XHS_STORAGE_STATE_PATH}" \
  --headless
```

The skill must not collect passwords, OTPs, captcha answers, or attempt to bypass platform checks. If login or security verification is required, return a blocked status and request a human refresh.

## Supported Auth Modes

### 1. Local Customer Bootstrap

Use when the customer can run a local browser:

1. Customer runs `xhs_login.py` or `login_xhs.ps1`.
2. The official Xiaohongshu page opens.
3. Customer scans/approves login.
4. Script saves `storage_state.json`.
5. Customer uploads the file to a secret manager or encrypted runtime volume.

This is the safest default for non-Codex agents because the agent never handles credentials.

### 2. Remote Visual Browser Handoff

Use when the job runs in cloud but the customer can open a temporary browser session:

1. Provision a short-lived headed browser session through noVNC, browserless, or an equivalent remote desktop/browser gateway.
2. Customer logs in on the official Xiaohongshu page.
3. Backend exports Playwright storage state.
4. Store the exported state as a secret.
5. Destroy the temporary browser session.

The model may coordinate the flow, but the user performs the login.

### 3. Pre-Provisioned Secret

Use for scheduled production jobs:

1. Store `storage_state.json` in the platform secret manager.
2. Mount it into the worker as `XHS_STORAGE_STATE_PATH`.
3. Pass only the path to the collector command.
4. Never include cookie contents in prompts, logs, summaries, or task JSON.

## Refresh and Failure States

The collector or scheduler should surface these states:

- `login_required`: No valid session is available.
- `security_verification`: Xiaohongshu requires manual verification.
- `captcha_required`: Stop and ask for a human refresh.
- `storage_state_missing`: Secret or mounted file is missing.
- `storage_state_expired`: Session exists but no longer grants access.

When one appears, pause collection for that account and refresh the login state manually.

## Deployment Guidance

- Treat `storage_state.json` as equivalent to an active login session.
- Store one state file per Xiaohongshu account.
- Do not share state files between customers.
- Do not commit state files to Git.
- Keep the model API away from raw cookies; tools may receive paths, not secret contents.
- Prefer fixed low-frequency schedules over aggressive polling.

## What Other Agents Need

Agents without browser control should not attempt login. They should:

1. Check that `XHS_STORAGE_STATE_PATH` exists.
2. Run collection.
3. If authentication fails, emit a structured action request: "Please refresh Xiaohongshu login state."

