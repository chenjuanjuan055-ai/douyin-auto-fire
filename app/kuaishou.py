"""Kuaishou web-message adapter.

This module deliberately supports only text and random-text messages in its
first release.  Kuaishou's web UI does not share Douyin's sticker, image, or
chat selectors, so pretending that those message types work would risk sending
to the wrong conversation or reporting a false success.
"""

from __future__ import annotations

import asyncio
import random
from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import Locator, Page

from app.browser import (
    AuthenticationError,
    BrowserSession,
    RiskControlError,
    SearchBoxNotReadyError,
    _any_visible,
    _first_visible_selector,
    open_browser,
)
from app.config import ConfigError
from app.douyin import PageOperationError
from app.models import Message, Settings


KUAISHOU_HOME_URL = "https://www.kuaishou.com/"

# All site-specific locators live here so the first live dry run can adjust a
# small, well-documented list rather than spreading Kuaishou details through
# the scheduler and sender code.
LOGIN_REQUIRED_MARKERS = (
    'text=扫码登录',
    'text=手机号登录',
    'text=登录后',
    '[class*="login"] [class*="qrcode"]',
)
RISK_MARKERS = (
    'text=安全验证',
    'text=验证身份',
    'text=请完成验证',
    'text=访问异常',
)
PRIVATE_MESSAGE_ENTRIES = (
    'a:has-text("私信")',
    'a:has-text("消息")',
    '[role="link"]:has-text("私信")',
    '[role="button"]:has-text("私信")',
)
SEARCH_INPUTS = (
    'input[placeholder*="搜索"]',
    'input[aria-label*="搜索"]',
    '[role="textbox"][placeholder*="搜索"]',
    '[contenteditable="true"][data-placeholder*="搜索"]',
)
MESSAGE_INPUTS = (
    'textarea[placeholder*="消息"]',
    'textarea[placeholder*="发送"]',
    '[contenteditable="true"][data-placeholder*="消息"]',
    '[contenteditable="true"][aria-label*="消息"]',
    '[contenteditable="true"][role="textbox"]',
)
SEND_BUTTONS = (
    'button:has-text("发送")',
    '[role="button"]:has-text("发送")',
    '[data-e2e*="send"]',
    '[class*="send"] button',
)
SEND_FAILURE_MARKERS = (
    'text=发送失败',
    'text=发送频繁',
    'text=请稍后再试',
)

SEARCH_BOX_RETRIES = 3
RETRY_DELAY_MS = 1_500


@asynccontextmanager
async def open_kuaishou(settings: Settings) -> AsyncIterator[BrowserSession]:
    async with open_browser(
        settings,
        storage_state_label="KUAISHOU_STORAGE_STATE",
        cookie_label="KUAISHOU_COOKIE",
    ) as session:
        yield session


async def verify_login(page: Page, timeout_ms: int = 15_000) -> None:
    if await _any_visible(page, RISK_MARKERS, timeout_ms=2_000):
        raise RiskControlError("快手要求进行安全验证，任务已停止")
    if await _any_visible(page, LOGIN_REQUIRED_MARKERS, timeout_ms=2_000):
        raise AuthenticationError("快手登录状态已失效")
    if not await _any_visible(page, PRIVATE_MESSAGE_ENTRIES + SEARCH_INPUTS, timeout_ms=timeout_ms):
        raise AuthenticationError("未检测到快手私信入口，登录状态可能失效或网页结构已变化")


async def open_private_messages(page: Page, timeout_ms: int = 15_000) -> None:
    """Open Kuaishou's web private-message UI without relying on a guessed URL."""
    await page.goto(KUAISHOU_HOME_URL, wait_until="domcontentloaded", timeout=45_000)
    if await _any_visible(page, RISK_MARKERS, timeout_ms=2_000):
        raise RiskControlError("快手页面要求进行安全验证，任务已停止")
    if await _any_visible(page, LOGIN_REQUIRED_MARKERS, timeout_ms=2_000):
        raise AuthenticationError("进入快手页面后登录状态失效")

    # On some layouts the message search field is already visible.  Otherwise
    # use the visible private-message entry, which avoids hard-coding a URL that
    # may vary by account or current Kuaishou web release.
    if not await _first_visible_selector(page, SEARCH_INPUTS, timeout_ms=1_000):
        entry = await _first_visible_locator(page, PRIVATE_MESSAGE_ENTRIES, timeout_ms)
        if entry is None:
            raise SearchBoxNotReadyError("未找到快手私信入口；请在 Dry Run 的截图中确认网页版是否提供私信")
        await entry.click()

    for attempt in range(1, SEARCH_BOX_RETRIES + 1):
        matched = await _first_visible_selector(page, SEARCH_INPUTS, timeout_ms)
        if matched is not None:
            await page.wait_for_timeout(2_000)
            return
        if await _any_visible(page, RISK_MARKERS, timeout_ms=2_000):
            raise RiskControlError("快手私信页面要求进行安全验证，任务已停止")
        if await _any_visible(page, LOGIN_REQUIRED_MARKERS, timeout_ms=2_000):
            raise AuthenticationError("进入快手私信页面后登录状态失效")
        if attempt < SEARCH_BOX_RETRIES:
            await page.wait_for_timeout(RETRY_DELAY_MS)

    raise SearchBoxNotReadyError("快手私信页已打开，但搜索框在多次重试后仍未就绪")


class KuaishouChat:
    def __init__(self, page: Page, timeout_ms: int = 15_000) -> None:
        self.page = page
        self.timeout_ms = timeout_ms

    async def open_target(self, name: str, retries: int = 1) -> None:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                search = await _first_visible_locator(self.page, SEARCH_INPUTS, self.timeout_ms)
                if search is None:
                    raise PageOperationError("找不到快手好友搜索框")
                await search.click()
                await search.fill("")
                await search.fill(name)
                await self.page.wait_for_timeout(1_500)
                result = await self._search_result(name)
                if result is None:
                    raise PageOperationError("搜索不到快手目标好友")
                await result.click(force=True)
                await self._confirm_composer()
                return
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    await self.page.wait_for_timeout(RETRY_DELAY_MS)
        if last_error is not None:
            raise last_error
        raise PageOperationError("打开快手聊天失败")

    async def message_input(self) -> Locator:
        editor = await _first_visible_locator(self.page, MESSAGE_INPUTS, self.timeout_ms)
        if editor is None:
            raise PageOperationError("找不到快手消息输入框")
        return editor

    async def _search_result(self, name: str) -> Locator | None:
        result_selectors = (
            '[class*="search"] [class*="item"]',
            '[class*="Search"] [class*="Item"]',
            '[data-e2e*="search"] [role="listitem"]',
            '[role="listitem"]',
        )
        for selector in result_selectors:
            rows = self.page.locator(selector).filter(has_text=name)
            for index in range(await rows.count()):
                row = rows.nth(index)
                if await row.is_visible():
                    return row

        for candidate_group in (self.page.get_by_text(name, exact=True), self.page.get_by_text(name, exact=False)):
            for index in range(await candidate_group.count()):
                candidate = candidate_group.nth(index)
                if await candidate.is_visible():
                    return candidate
        for selector in (f'[title="{_css_escape(name)}"]', f'[aria-label="{_css_escape(name)}"]'):
            candidate = self.page.locator(selector).first
            if await candidate.count() and await candidate.is_visible():
                return candidate
        return None

    async def _confirm_composer(self) -> None:
        deadline = asyncio.get_running_loop().time() + self.timeout_ms / 1000
        while asyncio.get_running_loop().time() < deadline:
            if await _first_visible_locator(self.page, MESSAGE_INPUTS, timeout_ms=500):
                return
            if await _any_visible(self.page, RISK_MARKERS, timeout_ms=500):
                raise RiskControlError("快手要求进行安全验证，任务已停止")
            await self.page.wait_for_timeout(500)
        raise PageOperationError("已选中好友，但快手消息输入框未出现")


async def send_message(page: Page, chat: KuaishouChat, message: Message) -> None:
    if message.type == "random":
        await send_message(page, chat, random.choice(message.choices))
        return
    if message.type != "text":
        raise ConfigError("快手首版仅支持 text 或 random(text) 消息；图片和抖音原生表情尚未实现")
    content = message.content or ""
    editor = await chat.message_input()
    before_count = await page.get_by_text(content, exact=True).count()
    await editor.click()
    await page.keyboard.insert_text(content)
    await _trigger_send(page)
    await _confirm_text_sent(page, editor, content, before_count)


async def _trigger_send(page: Page) -> None:
    button = await _first_visible_locator(page, SEND_BUTTONS, timeout_ms=1_500)
    if button is not None:
        await button.click()
        return
    await page.keyboard.press("Enter")


async def _confirm_text_sent(page: Page, editor: Locator, content: str, before_count: int) -> None:
    deadline = asyncio.get_running_loop().time() + 15
    while asyncio.get_running_loop().time() < deadline:
        if await _any_visible(page, SEND_FAILURE_MARKERS, timeout_ms=300):
            raise PageOperationError("快手页面提示消息发送失败")
        # A contenteditable composer can itself match get_by_text(content).
        # Treat a new text match as sent only after the composer has cleared;
        # otherwise a failed click could be reported as a successful message.
        if await page.get_by_text(content, exact=True).count() > before_count and not await _composer_has_text(editor, content):
            await page.wait_for_timeout(1_000)
            return
        await page.wait_for_timeout(300)
    raise PageOperationError("快手消息可能已提交，但未检测到新增的已发送文本")


async def _composer_has_text(editor: Locator, content: str) -> bool:
    return bool(
        await editor.evaluate(
            """(element, expected) => {
                const raw = "value" in element ? element.value : (element.innerText || element.textContent || "");
                const normalize = value => (value || "").replace(/[\\s\\u200B\\u200C\\u200D\\uFEFF]+/g, " ").trim();
                return normalize(raw).includes(normalize(expected));
            }""",
            content,
        )
    )


async def _first_visible_locator(page: Page, selectors: tuple[str, ...], timeout_ms: int) -> Locator | None:
    per_selector = max(250, timeout_ms // max(1, len(selectors)))
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=per_selector)
            return locator
        except Exception:
            continue
    return None


def _css_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
