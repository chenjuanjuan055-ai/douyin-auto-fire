# 快手网页私信（实验性）

本仓库新增了一个与抖音流程隔离的快手网页私信适配器。它目前只支持文字消息和随机文字消息，且默认只有手动触发，避免未验证时自动发送。

## 先决条件

1. 用电脑浏览器登录快手网页版，并确认该账号在网页端能打开私信、搜索好友、发送文字。
2. 用 Cookie-Editor 导出快手域名的完整 Cookie JSON 数组。
3. 不要导出、上传或分享抖音 Cookie；两个平台的 Cookie 不可混用。

## 配置 GitHub Secrets

在 Fork 仓库的 `Settings → Secrets and variables → Actions` 添加：

| Secret | 内容 |
| --- | --- |
| `KUAISHOU_COOKIE` | 快手网页版导出的完整 Cookie JSON 数组 |
| `KUAISHOU_CONFIG` | 根据 `config.kuaishou.example.json` 填写的完整 JSON |

`KUAISHOU_CONFIG` 的首版消息仅可使用：

```json
{"type": "text", "value": "续火花 ✨"}
```

或多个文字候选项组成的 `random`。图片、快手原生表情暂未实现，配置它们会明确失败，而不会静默误发。

## 验证顺序

1. 在 `Actions → Send Kuaishou Messages (Experimental)` 点击 `Run workflow`。
2. 保持 `dry_run = true`。这一步只验证登录和每个好友的聊天窗口，不发送消息。
3. 如果失败，在运行页面下载 `kuaishou-failure-*` 诊断文件；其中截图可用于更新 `app/kuaishou.py` 中的选择器。请勿公开截图，它们可能包含私信内容。
4. Dry Run 绿色成功后，只保留一个测试好友，手动设置 `dry_run = false` 运行一次。

## 定时发送

工作流故意没有预置 `schedule`。快手网页端的私信入口和 GitHub 云端 IP 的风控需要先由真实 Dry Run 验证。

确认真实发送成功后，在 `.github/workflows/kuaishou-send.yml` 的 `on:` 下增加：

```yml
  schedule:
    - cron: "0 1 * * *"
      timezone: "Asia/Shanghai"
```

它表示每天北京时间凌晨 1:00 运行。定时运行会真实发送；不需要电脑开机，但 Cookie 失效、安全验证或网页结构改变会导致失败。
