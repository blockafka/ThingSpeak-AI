#!/usr/bin/env python3
"""
Non-interactive Xiaohongshu login-state bootstrap (DOM-based detection).

Opens a visible browser; the user logs in manually (QR / official flow).
Login is detected by the DOM, NOT by cookies (anonymous sessions already
carry web_session / a1 / gid, so cookie presence is unreliable).

Detection logic:
  1. Wait until the logged-out baseline is observed: a visible "登录" entry.
  2. After that baseline is seen, wait until the "登录" entry disappears and a
     user avatar / "我的主页" entry appears, sustained for several polls.
  3. Then save Playwright storage_state.json and exit.

Never reads/stores passwords or OTPs. Only persists the Playwright storage
state (a logged-in browser session) which must be treated as a secret.

Exit codes:
  0  login detected and storage state saved
  3  timeout / login not detected (storage state NOT written)
  2  playwright not installed
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_STORAGE = "data/xhs/auth/storage_state.json"
LOGIN_URL = "https://www.xiaohongshu.com/explore"
TIMEOUT_MINUTES = 12
STABLE_CHECKS = 3        # 连续命中“已登录”次数（每次间隔 POLL_SECONDS）后确认
POLL_SECONDS = 2
MIN_ELAPSED_SECONDS = 8  # 最少等待，避免初始渲染抖动


def launch_browser(playwright: Any):
    errors: list[str] = []
    for channel in ("chrome", "msedge", None):
        try:
            args: dict[str, Any] = {"headless": False}
            if channel:
                args["channel"] = channel
            return playwright.chromium.launch(**args)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{channel or 'playwright-chromium'}: {exc}")
    raise RuntimeError("无法启动 Chromium 浏览器:\n" + "\n".join(errors))


def login_button_visible(page: Any) -> bool:
    """页面右上角/弹窗里是否存在可见的“登录”入口（未登录基线）。"""
    try:
        loc = page.locator("xpath=//*[normalize-space(text())='登录' or normalize-space(text())='登录/注册']")
        n = min(loc.count(), 5)
        for i in range(n):
            try:
                if loc.nth(i).is_visible():
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def logged_in_marker(page: Any) -> bool:
    """是否存在登录后才有的标志：指向用户主页的头像/链接。"""
    selectors = [
        "a[href*='/user/profile/'] img",
        ".main-container .user .reds-avatar",
        ".side-bar .user",
        "li.user.side-bar-component",
        ".reds-avatar img",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                return True
        except Exception:
            continue
    return False


def main() -> int:
    storage_state = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_STORAGE)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright 未安装。请先运行: python -m pip install -r requirements.txt", file=sys.stderr)
        return 2

    storage_state.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        context = browser.new_context(
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": 1365, "height": 900},
        )
        page = context.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)

        print("=" * 56, flush=True)
        print("浏览器已打开，请在弹出的窗口里扫码登录小红书。", flush=True)
        print("脚本不会读取账号密码，会等你真正登录后(“登录”按钮消失)再保存。", flush=True)
        print(f"最长等待 {TIMEOUT_MINUTES} 分钟，登录成功后自动保存并退出。", flush=True)
        print("=" * 56, flush=True)

        start = time.time()
        deadline = start + TIMEOUT_MINUTES * 60
        seen_baseline = False
        stable = 0
        ok = False
        ticks = 0
        while time.time() < deadline:
            elapsed = time.time() - start
            has_login_btn = login_button_visible(page)
            has_marker = logged_in_marker(page)

            if has_login_btn:
                seen_baseline = True
                stable = 0
            elif seen_baseline and elapsed >= MIN_ELAPSED_SECONDS and (has_marker or not has_login_btn):
                # 见过“登录”基线后，它消失了 → 视为已登录
                stable += 1
                if stable >= STABLE_CHECKS:
                    ok = True
                    break

            ticks += 1
            if ticks % 15 == 0:
                print(f"...等待登录中 ({int(elapsed)}s) baseline_seen={seen_baseline}", flush=True)
            time.sleep(POLL_SECONDS)

        if ok:
            time.sleep(2)
            context.storage_state(path=str(storage_state))
            cookie_count = len(context.cookies())
            print(f"LOGIN_OK saved={storage_state} cookies={cookie_count}", flush=True)
            rc = 0
        else:
            print("LOGIN_TIMEOUT 未检测到登录态，未保存登录态文件。", flush=True)
            rc = 3

        context.close()
        browser.close()

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
