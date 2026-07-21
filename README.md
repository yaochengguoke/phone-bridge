# Phone Bridge
手机 ↔ AI 双向桥。手机浏览器打字 → PC 上的 Claude Code 处理 → 回复推回手机。

**零依赖平台、零注册、模型可换。一个 Python 文件。**

## 特性
- 自有 Web 聊天界面，手机浏览器直接打开
- 调用 Claude Code CLI（支持 DeepSeek 等第三方模型）
- 会话记忆——连续对话不断片
- MCP 模式——Claude Code 原生集成
- 消息 JSON 持久化
- 可插拔 AI 后端

## 快速开始

### 1. 前提
- Python 3.11+
- [Claude Code](https://claude.ai/code) 已安装并登录

### 2. 安装
```bash
git clone https://github.com/yourname/phone-bridge.git
cd phone-bridge
pip install flask mcp
```

### 3. 配置（可选）
复制 `.env.example` 为 `.env`，按需修改：
```bash
cp .env.example .env
```

不配也能跑——默认用当前目录作为工作区。

### 4. 启动
```bash
python phone_bridge.py --standalone
```

浏览器打开 `http://localhost:9010` 看到聊天界面。

### 5. 手机访问
用 Cloudflare Tunnel（免费，无需注册）：
```bash
cloudflared tunnel --url http://localhost:9010
```
手机打开显示的 `https://xxx.trycloudflare.com` 地址。

## MCP 集成（可选）
在 Claude Code 配置中添加：
```json
{
  "mcpServers": {
    "phone-bridge": {
      "command": "python",
      "args": ["C:\\path\\to\\phone_bridge.py"]
    }
  }
}
```
重启 Claude Code 后可用 `check_phone_messages` / `send_phone_message` 工具。

## AI 后端

`.env` 里改 `AI_BACKEND` 一键切换：

**Claude Code** (默认，支持 DeepSeek 等第三方模型)
```bash
AI_BACKEND=claude
# 前提: Claude Code 已安装并登录
```

**Codex CLI**
```bash
AI_BACKEND=codex
# 前提: npm install -g @openai/codex
```

**直接调 API** (DeepSeek / OpenAI / Groq)
```bash
AI_BACKEND=api
API_KEY=sk-xxx
API_BASE=https://api.deepseek.com
API_MODEL=deepseek-chat
```

## 手机访问

需要隧道穿透内网。任选一种：

**Cloudflare Tunnel** (免费，无需注册)
```bash
cloudflared tunnel --url http://localhost:9010
```

**Tailscale** (免费，国内可用)
```
PC 和手机各装 Tailscale → 手机浏览器打开 http://<PC的Tailscale IP>:9010
```

## 配置项

| 变量 | 默认 | 说明 |
|------|------|------|
| AI_BACKEND | claude | claude / codex / api |
| WORK_DIR | . | AI 工作目录 |
| SYSTEM_PROMPT | - | 自定义 AI 角色 |
| AI_TIMEOUT | 300 | 超时秒数 |
| PORT | 9010 | Web 端口 |
| API_KEY | - | API 模式密钥 |
| API_BASE | api.deepseek.com | API 地址 |
| API_MODEL | deepseek-chat | 模型名 |

## 工作流程

```
手机浏览器 → 隧道 → phone_bridge.py → Claude/Codex/API → 回复手机
                     ├─ Web 服务 (Flask)
                     ├─ Agent 线程 (后台自动处理)
                     └─ MCP 接口 (Claude Code 原生扩展)
```

## 优势

- **零注册** — 不绑 Telegram/微信/Discord，不注册任何账号
- **模型自由** — Claude/Codex/Direct API 一键切换，不锁厂商
- **越用越聪明** — 知识库自积累，纠正过的错误不犯第二次
- **跨平台** — Windows/Mac/Linux，启动命令完全一致
- **MCP 原生** — Claude Code 内直接调 `check_phone_messages`
- **一个文件** — 核心逻辑全在 `phone_bridge.py`，读代码 5 分钟

## 劣势

- **回复慢** — `claude -p` 冷启动 10s + 推理 15s，非实时聊天
- **幻觉得手动修** — AI 偶尔编造答案，需要用知识库纠正
- **免费隧道不稳** — cloudflared 地址重启会变，国内可能抽风
- **PC 必须开着** — 架构前提，没法绕过
- **不是产品** — 是个人工具，没有用户系统、权限管理、监控面板

## 适合谁

- 有自己交易/开发系统，想手机遥控的人
- 不想依赖第三方平台（Telegram/微信）的人
- 用 DeepSeek 等非 Anthropic 模型的人

## License

MIT
