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

## .env 配置项
| 变量 | 默认 | 说明 |
|------|------|------|
| WORK_DIR | 当前目录 | Claude 工作目录 |
| SYSTEM_PROMPT | 通用提示 | 自定义 AI 角色 |
| AI_BACKEND | claude | AI 后端(claude/codex) |
| AI_TIMEOUT | 300 | 超时秒数 |
| PORT | 9010 | Web 服务端口 |

## 工作原理
```
手机 → Cloudflare隧道 → phone_bridge.py → Claude Code CLI → DeepSeek → 回复
                        ├─ Web 服务 (Flask)
                        ├─ Agent 线程 (自动处理消息)
                        └─ MCP 接口 (Claude Code 原生调用)
```

MIT License
