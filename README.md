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

## License

MIT
