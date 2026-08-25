# 🔥 抖音自动续火花

[![GitHub stars](https://img.shields.io/github/stars/unmev/douyin-auto-fire?style=flat-square)](https://github.com/unmev/douyin-auto-fire/stargazers)
![Visitors](https://visitor-badge.laobi.icu/badge?page_id=unmev.douyin-auto-fire)

> 定时自动向抖音好友发送消息，保持火花不断。基于 Playwright 模拟真实浏览器操作，可使用 GitHub Actions、云服务器或 Windows 电脑定时运行。

![douyin-auto-fire-banner.svg](https://img.908988.xyz/file/教程/douyin-auto-fire/5pdab8It.svg)

## 项目介绍

`douyin-auto-fire` 是一个基于 Python + Playwright 的抖音私信自动发送工具。

通过模拟浏览器操作，可以按照配置自动向指定好友发送文字、图片或抖音原生表情，并支持多种运行方式。

如果只是想快速使用，推荐 **GitHub Actions**：不需要自己购买服务器，也不需要电脑长期保持开机。也可以部署到 Linux 云服务器，或者直接在 Windows 电脑上运行。

> ⚠️ 本项目使用 Cookie / Storage State 作为登录凭证。请只保存在安全位置，不要提交到公开仓库，也不要分享给他人。

## ✨ 已实现功能

- ⏰ **定时自动发送**：支持 GitHub Actions、systemd Timer 等方式定时运行
- 💬 **多种消息类型**：支持文字、图片（PNG/JPG/GIF/WebP）和抖音原生表情
- 🎲 **随机消息**：支持从多条候选消息中随机选择
- 👥 **多好友支持**：可以同时为多个好友配置发送任务
- 👤 **多账号支持**：GitHub Actions 当前最多支持 5 个抖音账号
- 🧪 **Dry Run 模式**：只验证登录状态和好友定位，不真实发送消息
- 🔒 **防重复发送**：支持记录发送历史，减少重复触发导致的重复发送
- 🔔 **钉钉通知**：支持通过钉钉机器人接收任务结果
- 🛡️ **失败诊断**：失败时可保存日志、页面截图和 Playwright Trace
- 🔐 **登录凭证灵活**：支持 Cookie 或浏览器 Storage State
- ⏱️ **模拟真人操作**：支持随机发送间隔和输入节奏

## 🚀 快速使用教程

根据自己的使用场景选择一种部署方式即可：

### ☁️ [GitHub Actions 部署 →](docs/github-actions.md)

**推荐大多数用户使用。** 无需服务器，电脑也不需要长期在线，Fork 后配置 Secrets 即可每天自动运行。

包含 Cookie 获取、配置生成、GitHub Secrets、Dry Run、定时任务、多账号和失败诊断等完整图文步骤。

### 🖥️ [云服务器部署 →](docs/server.md)

适合有 Linux VPS / 云服务器的用户。

使用 Python + Playwright + Headless Chromium 运行，并通过 `systemd Timer` 每天自动执行。教程包含环境安装、Cookie 配置、Dry Run、systemd 定时、日志查看和项目更新。

### 🪟 [Windows 电脑部署 →](docs/windows.md)

适合想先在自己的电脑上运行或长期使用 Windows 电脑挂机的用户。

支持直接运行项目自带的扫码登录脚本生成 `storage-state.json`，也可以使用 Cookie，并可通过 Windows 任务计划程序每天自动运行。

> 第一次使用无论选择哪种部署方式，都建议先配置 **1 个账号 + 1 个好友 + 1 条文字消息**，先执行 Dry Run，确认正常后再真实发送和增加其他配置。

## 🧰 技术栈

| 类别 | 内容 |
| --- | --- |
| 语言 | Python 3.11+ |
| 浏览器自动化 | [Playwright](https://playwright.dev/python/) + Chromium |
| 定时调度 | GitHub Actions / systemd Timer / Windows 任务计划程序 |
| 环境变量 | python-dotenv |
| 时区 | tzdata |
| 通知 | 钉钉机器人 Webhook |
| 支持平台 | Windows / macOS / Linux |

主要依赖：

```text
playwright>=1.54,<2
python-dotenv>=1.1,<2
tzdata>=2025.2
```

## ⚠️ 注意事项

- Cookie、Storage State 和发送配置不要直接提交到公开仓库。
- 修改好友、消息或表情配置后，建议先运行一次 Dry Run。
- 同一个抖音账号不要同时运行多个自动发送任务，避免重复发送。
- GitHub-hosted Runner 或云服务器网络环境可能触发抖音安全验证。
- 如果 Cookie / Storage State 失效或抖音要求验证码，需要本人重新完成登录验证。
- 抖音网页结构发生变化时，自动化功能可能需要同步适配。

## Star History

<a href="https://www.star-history.com/?repos=unmev%2Fdouyin-auto-fire&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=unmev/douyin-auto-fire&type=date&theme=dark&legend=top-left&sealed_token=TkydV0nYtjJ4qP2Nb5Y9f7po-HgwD2pBSxu77UV_GBPhEVJk1qucxdlno9qqdKfANCMyyjgMRjk4QWqZlHQsHJbB3sEPxDIc3ExjCvi-uNJ1crMXnMCytA" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=unmev/douyin-auto-fire&type=date&legend=top-left&sealed_token=TkydV0nYtjJ4qP2Nb5Y9f7po-HgwD2pBSxu77UV_GBPhEVJk1qucxdlno9qqdKfANCMyyjgMRjk4QWqZlHQsHJbB3sEPxDIc3ExjCvi-uNJ1crMXnMCytA" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=unmev/douyin-auto-fire&type=date&legend=top-left&sealed_token=TkydV0nYtjJ4qP2Nb5Y9f7po-HgwD2pBSxu77UV_GBPhEVJk1qucxdlno9qqdKfANCMyyjgMRjk4QWqZlHQsHJbB3sEPxDIc3ExjCvi-uNJ1crMXnMCytA" />
 </picture>
</a>

## 友情链接

- [LINUX DO](https://linux.do/) - 新的理想型社区

## License

本项目采用 [MIT License](LICENSE)。
