# -*- coding: utf-8 -*-
"""
Phone Bridge — 手机 ↔ AI 双向桥
手机浏览器 → Cloudflare Tunnel → PC → Claude Code → 回复
支持 Claude Code / Codex CLI, 模型可插拔. 零外部依赖, 零注册.
"""
import json, os, sys, time, queue, threading, uuid, subprocess, shutil
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MSG_FILE = os.path.join(BASE_DIR, 'messages.json')
ENV_FILE = os.path.join(BASE_DIR, '.env')

# ======== Config ========
def load_env():
    """从 .env 加载配置, 没有则用默认值"""
    cfg = {
        'WORK_DIR': BASE_DIR,
        'AI_BACKEND': 'claude',       # claude | codex
        'AI_TIMEOUT': 300,
        'SYSTEM_PROMPT': '你是AI助手。回复要求: 中文, 简洁, 直接给结论。',
        'ALLOWED_USERS': [],
        'PORT': 9010,
    }
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip(); v = v.strip().strip('"').strip("'")
                    if k == 'ALLOWED_USERS':
                        cfg[k] = [int(x.strip()) for x in v.split(',') if x.strip()]
                    elif k == 'PORT':
                        cfg[k] = int(v)
                    else:
                        cfg[k] = v
    return cfg

cfg = load_env()
_CTX_FILE = os.path.join(os.path.dirname(__file__), "量化数据", "agent_context.txt")
_USER_BG = open(_CTX_FILE, encoding="utf-8").read() if os.path.exists(_CTX_FILE) else ""

_KB_FILE = os.path.join(os.path.dirname(__file__), "量化数据", "knowledge.md")
_KNOWLEDGE = open(_KB_FILE, encoding="utf-8").read() if os.path.exists(_KB_FILE) else ""

SYSTEM_PROMPT = (
    "ReAct: Think->Act->Observe->Answer. 先查后答, 中文回复.\n"
    "=== Knowledge ===\n" + _KNOWLEDGE + "\n=== Context ===\n" + _USER_BG + "\n=== end ==="
)
WORK_DIR = r"C:\MyProject\返璞量化"

WORK_DIR = cfg['WORK_DIR']
PORT = cfg['PORT']

# ======== 消息持久化 ========
def load_messages():
    if not os.path.exists(MSG_FILE): return []
    with open(MSG_FILE, encoding='utf-8') as f: return json.load(f)

def save_messages(msgs):
    with open(MSG_FILE, 'w', encoding='utf-8') as f:
        json.dump(msgs, f, indent=2, ensure_ascii=False)

messages = load_messages()
to_phone = queue.Queue()

# Cloudflared URL tracking — read from file updated by cloudflared
_tunnel_url = ''
_tunnel_file = os.path.join(os.path.dirname(__file__), '量化数据', 'tunnel_url.txt')
if os.path.exists(_tunnel_file):
    try:
        with open(_tunnel_file) as f:
            _tunnel_url = f.read().strip()
    except: pass

def add_message(role, text, reply_to=None):
    msg = {'id': str(uuid.uuid4())[:8], 'role': role, 'text': text,
           'time': datetime.now().isoformat(), 'reply_to': reply_to, 'status': 'pending'}
    messages.append(msg)
    save_messages(messages)
    return msg

# ======== AI Backend (可插拔) ========
_last_session_id = None

class AIBackend:
    """AI 后端基类. 子类实现 call(prompt)."""
    def call(self, prompt: str, env: dict, timeout: int) -> str:
        raise NotImplementedError

class ClaudeCLI(AIBackend):
    """Claude Code CLI (支持 DeepSeek 等第三方模型)"""
    def call(self, prompt, env, timeout):
        global _last_session_id
        cmd = self._find_claude()
        if cmd is None:
            return '(claude not found - install Claude Code)'
        args = cmd + ['-p', '--output-format', 'text', '--add-dir', WORK_DIR]
        if _last_session_id:
            args.extend(['-r', _last_session_id])
        try:
            r = subprocess.run(args, input=prompt, capture_output=True, text=True,
                              timeout=timeout, cwd=WORK_DIR, env=env, encoding='utf-8', errors='replace')
            out = r.stdout.strip()
            import re
            sid = re.search(r'session[:\s]+([a-f0-9-]{8,})', r.stderr or '')
            if sid: _last_session_id = sid.group(1)
            if r.stderr and 'session' not in (r.stderr or '').lower():
                out += '\n' + r.stderr.strip()[:200]
            return out or '(empty)'
        except subprocess.TimeoutExpired:
            _last_session_id = None; return f'(timeout {timeout}s)'
        except Exception as e:
            _last_session_id = None; return f'(error: {e})'

    @staticmethod
    def _find_claude():
        claude = shutil.which('claude')
        if claude: return [claude]
        node = shutil.which('node') or (r'C:\Program Files\nodejs\node.exe' if sys.platform == 'win32' else 'node')
        if not os.path.exists(node): return None
        if sys.platform == 'win32':
            appdata = os.environ.get('APPDATA', '')
            cli = os.path.join(appdata, r'npm\node_modules\@anthropic-ai\claude-code\cli-wrapper.cjs')
        else:
            r = subprocess.run([node, '-e',
                'console.log(require("child_process").execSync("npm root -g").toString().trim())'],
                capture_output=True, text=True)
            cli = os.path.join(r.stdout.strip(), '@anthropic-ai', 'claude-code', 'cli-wrapper.cjs')
        return [node, cli] if os.path.exists(cli) else None

class CodexCLI(AIBackend):
    """OpenAI Codex CLI"""
    def call(self, prompt, env, timeout):
        codex = shutil.which('codex')
        if not codex:
            return '(codex not found - install: npm install -g @openai/codex)'
        try:
            r = subprocess.run([codex, 'exec', prompt], input=prompt,
                              capture_output=True, text=True, timeout=timeout,
                              cwd=WORK_DIR, env=env, encoding='utf-8', errors='replace')
            return r.stdout.strip() or '(empty)'
        except subprocess.TimeoutExpired:
            return f'(timeout {timeout}s)'
        except Exception as e:
            return f'(codex error: {e})'

class DirectAPI(AIBackend):
    """直接调 OpenAI 兼容 API (DeepSeek/OpenAI/Groq 等)"""
    def call(self, prompt, env, timeout):
        api_key = cfg.get('API_KEY', '')
        api_base = cfg.get('API_BASE', 'https://api.deepseek.com')
        model = cfg.get('API_MODEL', 'deepseek-chat')
        if not api_key:
            return '(API_KEY not set in .env)'
        try:
            import requests as req
            r = req.post(f'{api_base}/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={'model': model, 'messages': [
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': prompt}
                ]}, timeout=timeout)
            data = r.json()
            if 'choices' in data:
                return data['choices'][0]['message']['content']
            return f'(API error: {data})'
        except Exception as e:
            return f'(API error: {e})'

BACKENDS = {
    'claude': ClaudeCLI(),
    'codex': CodexCLI(),
    'api': DirectAPI(),
}

def get_backend():
    name = cfg.get('AI_BACKEND', 'claude')
    if name not in BACKENDS:
        return BACKENDS['claude'], f'(backend \"{name}\" not found, using claude)'
    return BACKENDS[name], ''

def _build_env():
    """构建子进程环境 (补全Windows PATH)"""
    env = os.environ.copy()
    if sys.platform == 'win32':
        paths = [r'C:\Program Files\nodejs', r'C:\Windows\System32', r'C:\Windows']
        env['PATH'] = ';'.join(paths) + ';' + env.get('PATH', '')
    return env

def agent_loop():
    """Agent 后台线程: 自动处理手机消息"""
    while True:
        try:
            time.sleep(3)
            new_msgs = [m for m in messages if m['role'] == 'user' and m['status'] == 'pending']
            if not new_msgs:
                continue
            for msg in new_msgs:
                msg['status'] = 'processing'
                save_messages(messages)
            user_text = ' | '.join(m['text'] for m in new_msgs)
            if user_text.strip().lower() in ['/new', '/reset']:
                global _last_session_id; _last_session_id = None
                reply_text = '(new session)'
            else:
                backend, warn = get_backend()
                prompt = f'{SYSTEM_PROMPT}\n当前时间: {datetime.now()}\n用户: {user_text}'
                reply_text = backend.call(prompt, _build_env(), cfg['AI_TIMEOUT'])
                if warn:
                    reply_text = warn + '\n' + reply_text
            reply_to = new_msgs[0]['id']
            reply_msg = add_message('agent', reply_text, reply_to)
            reply_msg['status'] = 'done'
            for msg in new_msgs:
                msg['status'] = 'done'
            save_messages(messages)
            to_phone.put(reply_text)
        except Exception as e:
            print(f'agent error: {e}', file=sys.stderr)
            time.sleep(5)

# ======== Web 服务 ========
app = Flask(__name__)

HTML = r'''<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Phone Bridge</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font:16px/1.5 system-ui,sans-serif;background:#0d1117;color:#c9d1d9;height:100vh;display:flex;flex-direction:column}
#msgs{flex:1;overflow-y:auto;padding:12px}
.msg{margin:6px 0;padding:10px 14px;border-radius:12px;max-width:88%;word-wrap:break-word;line-height:1.4}
.msg.user{background:#1f6feb33;border:1px solid #1f6feb66;margin-left:auto;text-align:right}
.msg.bot{background:#21262d;border:1px solid #30363d}
.msg .t{font-size:11px;color:#8b949e;margin-bottom:4px}
#bar{display:flex;padding:10px;gap:6px;background:#161b22;border-top:1px solid #30363d}
#bar input{flex:1;padding:10px 14px;border:1px solid #30363d;border-radius:8px;background:#0d1117;color:#c9d1d9;font-size:15px;outline:none}
#bar input:focus{border-color:#1f6feb}
#bar button{padding:10px 16px;border:none;border-radius:8px;background:#1f6feb;color:#fff;font-size:15px;cursor:pointer}
#bar button:active{background:#1a5dc7}
.status{text-align:center;padding:4px;font-size:11px;color:#58a6ff}
.loading{opacity:.5;font-style:italic}
code{background:#30363d;padding:1px 6px;border-radius:4px;font-size:13px}
pre{background:#161b22;padding:8px;border-radius:6px;overflow-x:auto;font-size:13px;margin:6px 0}
</style></head><body>
<div id="msgs"></div><div class="status">connected</div>
<div id="bar"><input id="txt" placeholder="input..." autofocus><button onclick="send()">send</button></div>
<script>
let lastId=null;
async function loadMsgs(){
  try{const r=await fetch('/messages'+(lastId?'?since='+lastId:''));const msgs=await r.json();
    for(const m of msgs){
      const el=document.getElementById('loading-'+m.reply_to);if(el)el.remove();
      addMsg(m.text,m.role,m.id);lastId=m.id}}
  catch(e){}}
async function send(){
  const txt=document.getElementById('txt');const text=txt.value.trim();if(!text)return;txt.value='';
  const r=await fetch('/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
  const d=await r.json();addMsg(text,'user',d.id);
  document.getElementById('msgs').appendChild(Object.assign(document.createElement('div'),{id:'loading-'+d.id,className:'msg bot loading',innerHTML:'<div class=t>waiting</div>...'}));
  document.getElementById('msgs').scrollTop=99999}
function addMsg(text,role,id){
  if(document.getElementById('msg-'+id))return;
  let html=text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  html=html.replace(/```(\w*)\n([\s\S]*?)```/g,'<pre><code>$2</code></pre>');
  html=html.replace(/`([^`]+)`/g,'<code>$1</code>');
  html=html.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
  html=html.replace(/\n/g,'<br>');
  const d=document.createElement('div');d.className='msg '+(role==='user'?'user':'bot');d.id='msg-'+id;
  d.innerHTML='<div class=t>'+(role==='user'?'you':'AI')+' '+new Date().toLocaleTimeString()+'</div>'+html;
  document.getElementById('msgs').appendChild(d);document.getElementById('msgs').scrollTop=99999}
setInterval(loadMsgs,2000);loadMsgs();
</script></body></html>'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/send', methods=['POST'])
def send_msg():
    text = request.json.get('text', '').strip()
    if not text: return jsonify({'error': 'empty'})
    msg = add_message('user', text)
    return jsonify({'id': msg['id'], 'status': 'queued'})

@app.route('/messages')
def get_messages():
    since = request.args.get('since', '')
    result = []
    for m in messages:
        if since and m['id'] == since:
            result = []
        result.append(m)
    if since and result and result[0]['id'] == since:
        result = result[1:]
    return jsonify(result)

@app.route('/health')
def health():
    return jsonify({'ok': True, 'time': datetime.now().isoformat(), 'url': _tunnel_url})

def run_web():
    app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)

# ======== MCP Server (可选, Claude Code 集成用) ========
try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("phone-bridge")

    @mcp.tool()
    async def check_phone_messages() -> str:
        pending = [m for m in messages if m['role'] == 'user' and m['status'] == 'pending']
        if not pending: return '(no messages)'
        for m in pending:
            m['status'] = 'processing'; save_messages(messages)
        return '\n'.join(f"[{m['id']}] {m['text']}" for m in pending)

    @mcp.tool()
    async def send_phone_message(text: str) -> str:
        msg = add_message('agent', text)
        msg['status'] = 'done'; save_messages(messages)
        to_phone.put(text)
        return 'sent'

    @mcp.tool()
    async def phone_chat_history(n: int = 10) -> str:
        recent = messages[-n:] if len(messages) > n else messages
        if not recent: return '(no history)'
        lines = []
        for m in recent:
            role = {'user': 'User', 'agent': 'AI'}.get(m['role'], m['role'])
            lines.append(f"[{m['id']}] {role}: {m['text'][:300]}")
        return '\n'.join(lines)

    HAS_MCP = True
except ImportError:
    HAS_MCP = False

def start_standalone():
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=agent_loop, daemon=True).start()
    print(f'Phone Bridge: http://127.0.0.1:{PORT} | Agent running')
    try:
        while True: time.sleep(60)
    except KeyboardInterrupt:
        print('Stopped')

def start_mcp():
    if not HAS_MCP:
        print('MCP not available (pip install mcp)')
        return
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=agent_loop, daemon=True).start()
    print(f'Phone Bridge: http://127.0.0.1:{PORT} | Agent running | MCP ready')
    mcp.run(transport='stdio')

if __name__ == '__main__':
    if sys.stdin.isatty() or '--standalone' in sys.argv:
        start_standalone()
    else:
        start_mcp()
