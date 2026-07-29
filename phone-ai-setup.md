# 炎曦 Agent — 手机 AI 使用指南

> 最后更新：2026-07-29

## 架构

```
┌────────────────────────────────────────────────────────┐
│                      你的 Windows PC                    │
│                                                        │
│  phone_bridge.py (Flask :9010)                         │
│    ├─ Web Chat UI (/)           ← 手机浏览器访问        │
│    ├─ MCP Server (stdio)        ← Claude Code 集成      │
│    └─ Agent Loop (后台线程)      ← 自动处理手机消息      │
│         │                                              │
│         └─→ Claude Code CLI → AI 回复                   │
│              (读取 knowledge.md + agent_context.txt)     │
│                                                        │
│  alert_push.py                                         │
│    ├─ 15:00 日盘报告 → 企业微信推送                     │
│    ├─ 23:00 夜盘报告 → 企业微信推送                     │
│    └─ 实时告警 (崩溃/断连) → 企业微信推送               │
│                                                        │
│  tunnel_runner.py                                      │
│    └─ cloudflared tunnel → 公网 URL                     │
│         ├─ URL 变更 → 企业微信推送                       │
│         └─ 自动重启 (隧道死了自动拉起来)                 │
└────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   Cloudflare CDN              企业微信 Webhook
         │                              │
         ▼                              ▼
    📱 手机浏览器                  📱 企业微信
   (主动对话)                    (被动接收)
```

## 三种使用方式

### 方式一：企业微信推送（被动接收）

**你不需要做任何操作。** 系统自动推送：

| 时间 | 内容 |
|------|------|
| 每天 15:00 | 日盘报告：价差/RSI/HK 当日交易汇总 + 手机AI链接 |
| 每天 23:00 | 夜盘报告：同上 |
| 实时 | 引擎崩溃、API断连、策略熔断 |
| 实时 | 隧道 URL 变更通知 |
| 每天 15:00/23:00 | 策略自检报告（胜率低、连亏、盈亏比失衡） |

**效果示例：**
```
[日盘] 2026-07-29
  价差: 3笔 PnL=+156
  RSI: 1笔 PnL=+230
  HK: 0笔

手机: https://xxx.trycloudflare.com
```

### 方式二：手机浏览器（主动对话）

**最常用的方式。** 在手机上访问 https://xxx.trycloudflare.com

对话示例：
```
你: 现在持仓什么情况
AI: [读取 spread_daily_state.json]
    14对中 1对持仓: eg-v z=+1.78 SHORT
    ADX趋势: 玉米 SHORT, 白糖 SHORT
    其他引擎无持仓

你: 最近价差怎么样
AI: [读取 spread_daily_trades.csv]
    近10笔: SA-OI +86, SR-OI +42, ...
    总PnL +156, WR=60%

你: 检查引擎
AI: [ctypes检查PID]
    spread_daily(275516): OK
    bollinger_2h(271144): OK
    adx_trend(273840): OK
    rsi_live(274304): OK
    8/8 引擎运行中
```

AI 自动读取最新数据，不需你记文件路径。

### 方式三：PC 端直接对话

在本机终端或 Claude Code 中直接和 AI 对话。AI 能读取所有交易数据、日志、代码。

---

## 自己部署

### 前提

- Windows PC（24小时开机）
- Python 3.10+
- Node.js（Claude Code CLI 需要）
- Claude Code（`npm install -g @anthropic-ai/claude-code`）

### 第一步：企业微信机器人

1. 注册[企业微信](https://work.weixin.qq.com/)（个人免费）
2. 建一个群（可以只有自己）
3. 群设置 → 群机器人 → 添加 → 复制 Webhook URL
4. 把 URL 的 `key=xxx` 部分写入代码中

```
# alert_push.py 第 18 行
WXWORK_URL = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key'

# tunnel_runner.py 第 25 行
wx = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key'
```

> ⚠️ 安全提醒：key 是明文写在代码里的。不要把包含 key 的版本推到公开 GitHub。

### 第二步：Cloudflare Tunnel（免费）

1. 下载 [cloudflared.exe](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) 放到 `%USERPROFILE%\cloudflared.exe`
2. 不需要注册 Cloudflare 账号 — `trycloudflare.com` 是免费的临时隧道
3. `tunnel_runner.py` 会自动启动、获取 URL、推送到企业微信

```
# start_all.py 会自动起 tunnel_runner.py
# 或手动:
python tunnel_runner.py
```

隧道 URL 类似 `https://quick-fox-123.trycloudflare.com`，每次重启会变，自动推送到企业微信。

### 第三步：启动系统

```bash
cd C:\MyProject\返璞量化
cp .env.example .env    # 编辑 .env 设置 AI 后端
python start_all.py     # 一键启动所有引擎 + 手机AI
```

### 第四步：手机访问

企业微信会收到带 URL 的消息。点开链接，收藏到浏览器书签。URL 每次重启 PC 会变，但 `tunnel_runner.py` 会自动推送新 URL。

---

## 配置说明 (.env)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AI_BACKEND` | `claude` | AI 后端：`claude`(Claude Code CLI), `codex`(Codex CLI), `api`(DeepSeek/OpenAI) |
| `AI_TIMEOUT` | `300` | AI 最大响应时间（秒）|
| `PORT` | `9010` | 本地 Web 服务端口 |
| `ALLOWED_USERS` | (空) | 限制可访问的用户 |
| `API_KEY` | - | `api` 模式下的 API Key |
| `API_BASE` | `https://api.deepseek.com` | `api` 模式下的 API 地址 |
| `API_MODEL` | `deepseek-chat` | `api` 模式下的模型名 |

### 换 AI 模型

**Claude Code（默认，推荐）：**
```env
AI_BACKEND=claude
```
用本机已安装的 Claude Code CLI。支持 DeepSeek 等第三方模型。

**DeepSeek API（便宜但功能少）：**
```env
AI_BACKEND=api
API_KEY=sk-你的deepseek key
API_BASE=https://api.deepseek.com
API_MODEL=deepseek-chat
```

---

## 文件结构

| 文件 | 作用 |
|------|------|
| `phone_bridge.py` | 主服务：Web UI + MCP + Agent |
| `alert_push.py` | 企业微信推送 + 自检 |
| `tunnel_runner.py` | Cloudflare 隧道管理 |
| `start_all.py` | 一键启动所有进程 |
| `.env` | 配置（不上 git）|
| `量化数据/knowledge.md` | AI 知识库（自动积累）|
| `量化数据/agent_context.txt` | AI 上下文（你的背景信息）|

---

## 常见问题

**Q: 隧道 URL 打不开？**
- PC 上的 cloudflared 是否在运行：检查 `量化数据/tunnel.pid`
- 企业微信会收到最新 URL，用那个
- 手动重启 tunnel：`python tunnel_runner.py`

**Q: AI 不回复？**
- Claude Code CLI 是否安装：`claude --version`
- 检查 `phone_bridge.py` 是否在运行：读取 `量化数据/phone_bridge.pid`
- 看 `量化数据/phone_messages.json` 确认消息是否到达

**Q: 企业微信收不到推送？**
- Webhook key 是否正确
- 机器人是否还在群里（没被踢）
- `alert_push.py` 是否在运行

**Q: 安全吗？**
- trycloudflare.com 的 URL 是公开的，但 URL 本身是随机串，相当于密码
- 不需要注册 Cloudflare，不需要绑定信用卡
- 不建议在公开网络下使用（咖啡厅WiFi等）
- 企业微信 key 不要提交到公开 GitHub
