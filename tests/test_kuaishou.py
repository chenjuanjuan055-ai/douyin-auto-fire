from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import ConfigError, load_platform_settings
from app.kuaishou import KUAISHOU_HOME_URL, KuaishouChat, _composer_has_text, open_private_messages, send_message
from app.models import Message


def test_kuaishou_uses_separate_cookie_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("DOUYIN_COOKIE", raising=False)
    monkeypatch.setenv("KUAISHOU_COOKIE", '[{"name":"ks","value":"token","domain":".kuaishou.com"}]')
    monkeypatch.setenv("TASK_CONFIG", str(tmp_path / "config.json"))

    settings = load_platform_settings("kuaishou")

    assert settings.cookie is not None
    assert "token" in settings.cookie


def test_unknown_platform_is_rejected() -> None:
    with pytest.raises(ConfigError, match="不支持的平台"):
        load_platform_settings("unknown-platform")


@pytest.mark.asyncio
async def test_open_private_messages_uses_home_then_existing_search() -> None:
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()

    with patch("app.kuaishou._any_visible", new=AsyncMock(return_value=False)):
        with patch(
            "app.kuaishou._first_visible_selector",
            new=AsyncMock(return_value='input[placeholder*="搜索"]'),
        ):
            await open_private_messages(page)

    page.goto.assert_awaited_once_with(KUAISHOU_HOME_URL, wait_until="domcontentloaded", timeout=45_000)


@pytest.mark.asyncio
async def test_kuaishou_rejects_unsupported_message_types() -> None:
    with pytest.raises(ConfigError, match="仅支持 text 或 random"):
        await send_message(AsyncMock(), AsyncMock(spec=KuaishouChat), Message(type="image"))


@pytest.mark.asyncio
async def test_kuaishou_chat_reports_missing_message_input() -> None:
    page = MagicMock()
    chat = KuaishouChat(page)

    with patch("app.kuaishou._first_visible_locator", new=AsyncMock(return_value=None)):
        with pytest.raises(Exception, match="找不到快手消息输入框"):
            await chat.message_input()


@pytest.mark.asyncio
async def test_kuaishou_checks_composer_before_confirming_text() -> None:
    editor = MagicMock()
    editor.evaluate = AsyncMock(return_value=True)

    assert await _composer_has_text(editor, "续火花") is True
    assert editor.evaluate.await_args.args[1] == "续火花"
