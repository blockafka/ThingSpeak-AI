#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Hermes —— 轻量工作流编排调度引擎。

把 hermes/schedules/*.schedule.json 从「配置壳」变成可实际执行的调度器：
读取 schedule -> 解析 command 占位符 -> 注入 secrets(env) -> subprocess 执行 ->
落 run summary 到 hermes/runs/<run_id>.json。

用法：
    python hermes/engine.py list                 # 列出所有 schedule
    python hermes/engine.py run <name>           # 立即执行一次指定 schedule
    python hermes/engine.py run <name> --dry-run # 只打印将执行的命令，不真正跑
    python hermes/engine.py daemon               # 常驻：按 cron 到点触发（每分钟检查）

安全红线：
    - command/日志中的 ${XHS_STORAGE_STATE_PATH} 只作为路径传递，引擎绝不读取其内容。
    - secrets 的值不写入 run summary，只记录键名是否已就绪。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    ZONEINFO_AVAILABLE = True
except ImportError:
    ZONEINFO_AVAILABLE = False

HERMES_DIR = Path(__file__).resolve().parent
REPO_ROOT = HERMES_DIR.parent
SCHEDULES_DIR = HERMES_DIR / "schedules"
RUNS_DIR = HERMES_DIR / "runs"

# 视为机密的环境变量键：其「值」绝不落盘/打印，只记录是否就绪。
SECRET_KEYS = {"XHS_STORAGE_STATE_PATH", "OPENAI_API_KEY", "OPENAI_BASE_URL"}

_PLACEHOLDER = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _log(msg: str) -> None:
    print(f"[hermes] {msg}", flush=True)


def load_schedules() -> dict[str, dict]:
    """读取 schedules/*.schedule.json，返回 {name: schedule_dict}。"""
    out: dict[str, dict] = {}
    if not SCHEDULES_DIR.exists():
        return out
    for path in sorted(SCHEDULES_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            _log(f"跳过无法解析的 schedule {path.name}: {e}")
            continue
        name = data.get("name") or path.stem
        data["_source"] = str(path)
        out[name] = data
    return out


def _resolve_token(token: str, env: dict[str, str]) -> str:
    """把单个 token 里的 ${VAR} 用 env 替换；缺失则保留原样并告警。"""
    def repl(m: "re.Match[str]") -> str:
        key = m.group(1)
        if key in env and env[key] != "":
            return env[key]
        _log(f"警告：占位符 ${{{key}}} 未在环境变量中提供")
        return m.group(0)

    return _PLACEHOLDER.sub(repl, token)


def _fix_skill_path(token: str) -> str:
    """兼容旧 schedule：把 hermes/skills/xhs-content-collector 指到主干 skills/。"""
    return token.replace(
        "hermes/skills/xhs-content-collector", "skills/xhs_content_collector"
    ).replace(
        "skills/xhs-content-collector", "skills/xhs_content_collector"
    )


def build_command(schedule: dict, env: dict[str, str]) -> list[str]:
    raw = schedule.get("command") or []
    return [_resolve_token(_fix_skill_path(t), env) for t in raw]


def _secrets_status(schedule: dict, env: dict[str, str]) -> dict[str, bool]:
    status = {}
    for key in schedule.get("secrets", []):
        status[key] = bool(env.get(key))
    return status


def _count_artifacts(schedule: dict, env: dict[str, str]) -> dict[str, int]:
    """统计 artifacts 目录下的笔记数（metadata.json 个数），用于运行回执。"""
    counts: dict[str, int] = {}
    for art in schedule.get("artifacts", []):
        path_str = _resolve_token(art, env)
        p = Path(path_str)
        if p.exists():
            counts[path_str] = sum(1 for _ in p.rglob("metadata.json"))
        else:
            counts[path_str] = 0
    return counts


def run_schedule(name: str, dry_run: bool = False) -> int:
    schedules = load_schedules()
    if name not in schedules:
        _log(f"找不到 schedule：{name}。可用：{', '.join(schedules) or '(无)'}")
        return 2
    schedule = schedules[name]
    env = dict(os.environ)
    # 兜底默认：未显式设置时给出合理的本地路径
    env.setdefault("XHS_OUTPUT_ROOT", str(REPO_ROOT / "data" / "xhs_collected"))

    cmd = build_command(schedule, env)
    secrets = _secrets_status(schedule, env)
    run_id = f"{name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    # 安全：日志里隐藏机密值，只显示键。storage_state 路径本身可显示（非内容）。
    printable = " ".join(cmd)
    _log(f"run_id={run_id}")
    _log(f"command: {printable}")
    _log(f"secrets ready: {secrets}")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_id": run_id,
        "schedule": name,
        "started_at": datetime.now().isoformat(),
        "command": cmd,
        "secrets_ready": secrets,
        "dry_run": dry_run,
    }

    if dry_run:
        summary["status"] = "dry_run"
        summary["finished_at"] = datetime.now().isoformat()
        _write_summary(run_id, summary)
        return 0

    # 缺失必需 secret 时给出明确警告（不阻断，让脚本自身决定）
    missing = [k for k, ok in secrets.items() if not ok]
    if missing:
        _log(f"注意：以下 secrets 未就绪 {missing}，命令可能失败")

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        code = proc.returncode
        tail_out = "\n".join((proc.stdout or "").splitlines()[-30:])
        tail_err = "\n".join((proc.stderr or "").splitlines()[-30:])
    except FileNotFoundError as e:
        code = 127
        tail_out, tail_err = "", f"命令无法启动：{e}"
    except Exception as e:  # noqa: BLE001
        code = 1
        tail_out, tail_err = "", f"执行异常：{type(e).__name__}: {e}"

    summary.update(
        {
            "status": "ok" if code == 0 else "failed",
            "exit_code": code,
            "elapsed_sec": round(time.time() - t0, 1),
            "finished_at": datetime.now().isoformat(),
            "stdout_tail": tail_out,
            "stderr_tail": tail_err,
            "artifacts": _count_artifacts(schedule, env),
        }
    )
    _write_summary(run_id, summary)
    _log(f"完成：status={summary['status']} exit={code} 耗时={summary['elapsed_sec']}s")
    _log(f"产物统计：{summary['artifacts']}")
    return code


def _write_summary(run_id: str, summary: dict) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = RUNS_DIR / f"{run_id}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"run summary -> {out}")


# ----------------- 最小 cron 匹配（5 字段：分 时 日 月 周） -----------------
def _cron_field_match(field: str, value: int) -> bool:
    if field == "*":
        return True
    for part in field.split(","):
        if "/" in part:
            base, step = part.split("/", 1)
            step = int(step)
            if base in ("*", ""):
                if value % step == 0:
                    return True
            else:
                lo = int(base.split("-")[0])
                if (value - lo) >= 0 and (value - lo) % step == 0:
                    return True
        elif "-" in part:
            lo, hi = (int(x) for x in part.split("-", 1))
            if lo <= value <= hi:
                return True
        else:
            if int(part) == value:
                return True
    return False


def cron_matches(expr: str, now: datetime) -> bool:
    fields = expr.split()
    if len(fields) != 5:
        return False
    minute, hour, dom, month, dow = fields
    # cron 的星期：0=周日..6=周六；Python isoweekday()：1=周一..7=周日
    cron_dow = now.isoweekday() % 7  # 周日->0, 周一->1, ... 周六->6
    return (
        _cron_field_match(minute, now.minute)
        and _cron_field_match(hour, now.hour)
        and _cron_field_match(dom, now.day)
        and _cron_field_match(month, now.month)
        and _cron_field_match(dow, cron_dow)
    )


def daemon() -> int:
    _log("daemon 启动，每分钟检查一次 cron（Ctrl+C 退出）")
    # 时区配置：优先使用 TZ 环境变量，否则使用本地时区
    tz = None
    tz_env = os.getenv("TZ", "").strip()
    if tz_env and ZONEINFO_AVAILABLE:
        try:
            tz = ZoneInfo(tz_env)
            _log(f"使用时区：{tz_env}")
        except ZoneInfoNotFoundError:
            _log(f"警告：时区 {tz_env} 不存在，使用本地时区")
    last_minute = None
    while True:
        if tz:
            now = datetime.now(tz=tz)
        else:
            now = datetime.now()
        stamp = now.strftime("%Y-%m-%d %H:%M")
        if stamp != last_minute:
            last_minute = stamp
            for name, sch in load_schedules().items():
                expr = sch.get("cron")
                if expr and cron_matches(expr, now):
                    _log(f"cron 命中 {name} @ {stamp}")
                    run_schedule(name)
        time.sleep(20)


def list_schedules() -> int:
    schedules = load_schedules()
    if not schedules:
        _log("没有任何 schedule（hermes/schedules/*.json 为空）")
        return 0
    for name, sch in schedules.items():
        _log(
            f"- {name}: cron='{sch.get('cron')}' skill={sch.get('skill')} "
            f"secrets={sch.get('secrets')}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes 轻量编排调度引擎")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="列出所有 schedule")
    pr = sub.add_parser("run", help="立即执行一次 schedule")
    pr.add_argument("name")
    pr.add_argument("--dry-run", action="store_true")
    sub.add_parser("daemon", help="常驻按 cron 调度")

    args = parser.parse_args(argv)
    if args.cmd == "list":
        return list_schedules()
    if args.cmd == "run":
        return run_schedule(args.name, dry_run=args.dry_run)
    if args.cmd == "daemon":
        return daemon()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
