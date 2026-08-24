"""Run the Kuaishou adapter while reusing the project's safety facilities."""

from __future__ import annotations

import asyncio
import random

from app.browser import AuthenticationError, RiskControlError, SearchBoxNotReadyError, save_trace
from app.config import ConfigError, load_platform_settings, load_task
from app.history import AlreadyRunningError, History, run_lock
from app.kuaishou import KuaishouChat, open_kuaishou, open_private_messages, send_message, verify_login
from app.main import _configure_logging, _message_id, _notify_dingtalk, _screenshot, _trace_path, _write_results
from app.models import TargetResult
from app.privacy import build_target_aliases, target_alias


async def run(dry_run: bool = False, env_file: str | None = None) -> int:
    settings = load_platform_settings("kuaishou", env_file)
    task = load_task(settings)
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    aliases = build_target_aliases(task.targets)
    _configure_logging(settings.artifacts_dir, aliases, label="快手", reset=True)

    if not settings.storage_state and not settings.cookie:
        raise ConfigError("必须配置 KUAISHOU_STORAGE_STATE 或 KUAISHOU_COOKIE")

    history = History(settings.artifacts_dir / "history.json")
    run_date = history.run_date(task.timezone)
    results: list[TargetResult] = []
    screenshots = []
    fatal_error: Exception | None = None
    try:
        async with open_kuaishou(settings) as session:
            page = session.page
            trace_saved = False
            try:
                await open_private_messages(page)
            except Exception as exc:
                screenshot = await _screenshot(page, settings.artifacts_dir, "kuaishou-login")
                if screenshot:
                    screenshots.append(screenshot)
                if settings.trace:
                    await save_trace(session, _trace_path(settings.artifacts_dir))
                    trace_saved = True
                label = "登录检查" if isinstance(exc, (AuthenticationError, RiskControlError)) else "运行检查"
                results.append(TargetResult(target=label, status="failed", error=str(exc)))
                fatal_error = exc

            if fatal_error is None:
                chat = KuaishouChat(page, timeout_ms=int(task.target_open_timeout_seconds * 1000))
                for index, target in enumerate(task.targets):
                    sent = 0
                    alias = target_alias(index)
                    try:
                        await chat.open_target(target.name, retries=task.target_open_retries)
                        if not dry_run:
                            for message_index, message in enumerate(target.messages):
                                key = history.key(task.task_id, run_date, target.name, _message_id(message_index, message))
                                if task.prevent_duplicates and history.contains(key):
                                    continue
                                if task.prevent_duplicates:
                                    history.reserve(key)
                                await verify_login(page, timeout_ms=3_000)
                                await send_message(page, chat, message)
                                if task.prevent_duplicates:
                                    history.mark_success(key)
                                sent += 1
                                if message_index < len(target.messages) - 1:
                                    await asyncio.sleep(random.uniform(task.interval_min, task.interval_max))
                        results.append(TargetResult(target=target.name, status="success", sent=sent, target_alias=alias))
                    except (AuthenticationError, RiskControlError) as exc:
                        screenshot = await _screenshot(page, settings.artifacts_dir, alias)
                        if screenshot:
                            screenshots.append(screenshot)
                        results.append(TargetResult(target=target.name, status="failed", sent=sent, error=str(exc), target_alias=alias))
                        fatal_error = exc
                        break
                    except Exception as exc:
                        screenshot = await _screenshot(page, settings.artifacts_dir, alias)
                        if screenshot:
                            screenshots.append(screenshot)
                        results.append(TargetResult(target=target.name, status="failed", sent=sent, error=str(exc), target_alias=alias))
                        if not task.continue_on_error:
                            break
                    if index < len(task.targets) - 1 and not dry_run:
                        await asyncio.sleep(random.uniform(task.interval_min, task.interval_max))
            if settings.trace and not trace_saved:
                await session.context.tracing.stop()
    except Exception as exc:
        if fatal_error is None:
            fatal_error = exc
            results.append(TargetResult(target="运行检查", status="failed", error=str(exc)))

    _write_results(settings.artifacts_dir, task.task_id, dry_run, results, aliases)
    await _notify_dingtalk(settings, task.task_id, dry_run, results, screenshots)
    if fatal_error is not None:
        raise fatal_error
    return 1 if any(result.status == "failed" for result in results) else 0


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="向多个快手好友发送配置的文字消息")
    parser.add_argument("--dry-run", action="store_true", help="只验证登录和好友，不发送消息")
    parser.add_argument("--env-file", help="指定 .env 文件路径")
    args = parser.parse_args()
    try:
        settings = load_platform_settings("kuaishou", args.env_file)
        with run_lock(settings.artifacts_dir / "run.lock"):
            return asyncio.run(run(dry_run=args.dry_run, env_file=args.env_file))
    except (ConfigError, AuthenticationError, RiskControlError, SearchBoxNotReadyError, AlreadyRunningError) as exc:
        print(f"错误: {exc}")
        return 2
    except KeyboardInterrupt:
        print("任务已取消")
        return 130
