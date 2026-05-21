"""
港力工程 AI Server — Real AI Agent Backend
============================================
6 AI agents each with dedicated LLM endpoints.
Uses DeepSeek API (configurable). All agents do REAL work.

Setup:
  1. Copy .env.example to .env and fill in your keys
  2. Or set DEEPSEEK_API_KEY environment variable
  3. Run: bash start_server.sh
"""
import json, os, re, time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from collections import defaultdict

# Load .env file if present
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TG_TOKEN", "8264433914:***")
TELEGRAM_CHAT_ID = os.environ.get("TG_CHAT_ID", "210925281")
PORT = int(os.environ.get("PORT", 8520))
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.log")

def log(msg: str):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ---------------------------------------------------------------------------
# LLM Call
# ---------------------------------------------------------------------------
def call_llm(system_prompt: str, user_message: str, temperature=0.7, max_tokens=1000) -> str:
    """Call DeepSeek (or compatible) LLM API."""
    if not LLM_API_KEY:
        return "[AI 未配置 — 請設定 DEEPSEEK_API_KEY]"
    import http.client
    body = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    })
    try:
        parsed = urlparse(LLM_BASE_URL)
        conn = http.client.HTTPSConnection(parsed.netloc, timeout=30)
        path = parsed.path.rstrip("/") + "/v1/chat/completions"
        conn.request("POST", path, body=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}"
        })
        resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return f"[AI 暫時離線，請WhatsApp聯絡我哋 🙏]"

# ---------------------------------------------------------------------------
# Telegram Notification
# ---------------------------------------------------------------------------
def send_telegram(name: str, phone: str, message: str) -> bool:
    import http.client
    text = (
        f"🔔 <b>新客戶查詢！</b>\n\n"
        f"👤 <b>名：</b>{name}\n"
        f"📞 <b>電話：</b>{phone}\n"
        f"💬 <b>想查詢：</b>\n{message}\n\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    body = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}).encode("utf-8")
    try:
        conn = http.client.HTTPSConnection("api.telegram.org", timeout=10)
        conn.request("POST", f"/bot{TELEGRAM_BOT_TOKEN}/sendMessage", body=body,
                     headers={"Content-Type": "application/json; charset=utf-8"})
        resp = conn.getresponse()
        result = json.loads(resp.read())
        conn.close()
        ok = result.get("ok", False)
        log(f"Telegram {'OK' if ok else 'FAIL'}: {name}")
        return ok
    except Exception as e:
        log(f"Telegram error: {e}")
        return False

# ---------------------------------------------------------------------------
# AI Agent Prompts
# ---------------------------------------------------------------------------
QUOTEBOT_PROMPT = """你係港力工程嘅 QuoteBot，負責太陽能系統報價。
港力係機電署註冊電業承辦商，主管蔡新昌，全港服務。
服務：村屋太陽能、水電工程、打拆防水。

報價邏輯：
- 村屋 5kW ≈ $80,000-$100,000（連安裝+FiT申請）
- 村屋 8kW ≈ $120,000-$150,000
- 村屋 10kW ≈ $150,000-$180,000
- 學校/屋苑大型系統按 kW 計，每 kW 約 $15,000-$18,000
- 天台防水另加約 $15,000-$30,000
- FiT 上網電價約 $3-$5/度，4-6年回本

回應用廣東話口語，熱情友善，畀到實際數字範圍。結尾邀請客戶留電話約上門免費度尺。"""

SAVECALC_PROMPT = """你係港力工程嘅 SaveCalc，負責計算太陽能回本期。
港力係機電署註冊電業承辦商，全港服務。

計算邏輯：
- 香港每 kW 太陽能年發電約 1,100-1,200 度
- FiT 上網電價約 $3-$5/度（視乎系統大小）
- 村屋每月平均電費約 $800-$1,500
- 安裝太陽能後電費可減 50-80%
- 加上 FiT 收入，年回報約 $15,000-$30,000

回應用廣東話口語，根據客戶提供嘅資料計數。清晰列出：安裝成本、年發電量、年回報、回本期、25年總收益。"""

BOOKMATE_PROMPT = """你係港力工程嘅 BookMate，負責幫客預約上門度尺。
港力由蔡新昌主管親自上門睇位，免費報價。

可用時段（虛擬）：
- 星期一至六：上午 9:00-12:00 / 下午 2:00-6:00
- 星期日及公眾假期休息

回應用廣東話口語，收集：客戶稱呼、電話、地址、首選時段。
確認後話畀客知港力會 WhatsApp 確認。"""

HELPBOT_PROMPT = """你係港力工程嘅 HelpBot，AI 智能客服。
港力工程有限公司係機電署註冊電業承辦商，主管蔡新昌。
服務：太陽能安裝、FiT申請、水電工程、WR2年檢、打拆防水。
全港服務，村屋/學校/屋苑/私樓/工廈。
WhatsApp: +852 91234567
電郵: Kongpower28@gmail.com

FAQ：
- FiT 上網電價計劃延至 2033 年
- 一般 4-6 年回本
- 港力一條龍包 FiT 申請
- 太陽能板保養 20 年
- 免費上門評估

回應用廣東話口語，簡潔有用。如果唔知答案就話會轉交港力同事跟進。"""

RANKUP_PROMPT = """你係港力工程嘅 RankUp，SEO 優化專家。
幫港力工程網站做 SEO 分析同建議。

港力服務關鍵字：太陽能安裝、村屋太陽能、FiT上網電價、水電工程、WR2年檢、天台防水

請根據用戶提供嘅頁面內容，分析：
1. 關鍵字密度同分佈
2. Meta description 建議（150字內）
3. Title tag 建議（60字內）
4. H1/H2 標題建議
5. 內連結建議
6. Schema markup 建議

用廣東話回應，具體實用。"""

POSTGEN_PROMPT = """你係港力工程嘅 PostGen，社交媒體內容創作專家。
幫港力工程寫 Facebook / Instagram / Threads 出post。

風格：
- 廣東話口語
- 太陽能 = 慳錢 + 環保
- 強調 FiT 上網電價 = 屋頂變印鈔機
- 港力親身上門 = 可靠、一條龍
- 加 emoji
- 有 CTA（行動呼籲）
- 適合香港村屋/學校/屋苑客戶

平台分別：
- FB：長文（150-300字）+ 圖描述 + 3-5 hashtag
- IG：短 caption（50-100字）+ 視覺描述 + 5-8 hashtag
- Threads：短文（100-200字）純文字為主、語氣輕鬆似傾偈、1-2 hashtag

每次生成時會標明平台，格式：
📘 Facebook Post：
[內容]

📸 Instagram Post：
[內容]

🧵 Threads Post：
[內容]"""

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------
_rate_limit = defaultdict(list)

def check_rate(ip: str) -> bool:
    now = datetime.now().timestamp()
    _rate_limit[ip] = [t for t in _rate_limit[ip] if now - t < 60]
    if len(_rate_limit[ip]) >= 10:
        return False
    _rate_limit[ip].append(now)
    return True

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

def json_response(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    for k, v in cors_headers().items():
        handler.send_header(k, v)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            json_response(self, {"status": "ok", "agents": 6, "time": datetime.now().isoformat()})
        elif path == "/game" or path == "/game/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            game_path = r"C:\Users\Administrator\Desktop\automatic\Roblox中文遊戲\roblox_3d_chinese.html"
            try:
                with open(game_path, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            except FileNotFoundError:
                json_response(self, {"error": "game file not found"}, 404)
        elif path == "/api/agents":
            json_response(self, {
                "agents": [
                    {"id":"quotebot","name":"QuoteBot","emoji":"💬","role":"Send相→AI即時估價","endpoint":"/api/quote"},
                    {"id":"savecalc","name":"SaveCalc","emoji":"🧮","role":"入電費單→AI計回本期","endpoint":"/api/calc"},
                    {"id":"bookmate","name":"BookMate","emoji":"📅","role":"24/7幫客book上門度尺","endpoint":"/api/book"},
                    {"id":"helpbot","name":"HelpBot","emoji":"🤖","role":"AI智能客服秒回","endpoint":"/api/chat"},
                    {"id":"rankup","name":"RankUp","emoji":"📈","role":"SEO優化·Google排名","endpoint":"/api/rankup"},
                    {"id":"postgen","name":"PostGen","emoji":"✍️","role":"社交媒體自動出post","endpoint":"/api/postgen"},
                ]
            })
        else:
            json_response(self, {"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        ip = self.client_address[0]

        if not check_rate(ip):
            json_response(self, {"error": "太快喇，請等一陣"}, 429)
            return

        # Parse body
        length = int(self.headers.get("Content-Length", 0))
        # Parse body (handle both UTF-8 and GBK encoding from Windows)
        raw_bytes = self.rfile.read(length)
        try: raw = raw_bytes.decode("utf-8")
        except: raw = raw_bytes.decode("gbk", errors="replace")
        try:
            params = json.loads(raw) if raw else {}
        except:
            params = parse_qs(raw)
            params = {k: (v[0] if isinstance(v, list) else v) for k, v in params.items()}

        # ──── AI Agent Routes ────
        if path == "/api/quote":
            msg = params.get("message", params.get("description", ""))
            if not msg:
                json_response(self, {"error": "請描述你嘅屋頂情況（幾大、咩類型）"}, 400)
                return
            log(f"QuoteBot: {msg[:80]}...")
            reply = call_llm(QUOTEBOT_PROMPT, msg)
            json_response(self, {"agent": "QuoteBot", "reply": reply})

        elif path == "/api/calc":
            msg = params.get("message", params.get("data", ""))
            if not msg:
                json_response(self, {"error": "請提供你嘅電費單資料 / 屋頂面積"}, 400)
                return
            log(f"SaveCalc: {msg[:80]}...")
            reply = call_llm(SAVECALC_PROMPT, msg, temperature=0.3)
            json_response(self, {"agent": "SaveCalc", "reply": reply})

        elif path == "/api/book":
            name = params.get("name", "").strip()
            phone = params.get("phone", "").strip()
            msg = params.get("message", "").strip()
            if not name or not phone:
                json_response(self, {"error": "請提供你嘅名同電話"}, 400)
                return
            log(f"BookMate: {name} | {phone}")
            prompt = f"客戶：{name}\n電話：{phone}\n備註：{msg}"
            reply = call_llm(BOOKMATE_PROMPT, prompt, temperature=0.5)
            # Also send Telegram notification
            send_telegram(name, phone, f"[📅 BookMate 預約]\n備註：{msg}")
            json_response(self, {"agent": "BookMate", "reply": reply, "booked": True})

        elif path == "/api/chat":
            msg = params.get("message", "")
            if not msg:
                json_response(self, {"error": "你想問咩呀？"}, 400)
                return
            log(f"HelpBot: {msg[:80]}...")
            reply = call_llm(HELPBOT_PROMPT, msg, temperature=0.6)
            json_response(self, {"agent": "HelpBot", "reply": reply})

        elif path == "/api/rankup":
            msg = params.get("message", params.get("content", ""))
            if not msg:
                json_response(self, {"error": "請提供你想分析嘅頁面內容"}, 400)
                return
            log(f"RankUp: analyzing content ({len(msg)} chars)")
            reply = call_llm(RANKUP_PROMPT, msg, temperature=0.4, max_tokens=1500)
            json_response(self, {"agent": "RankUp", "reply": reply})

        elif path == "/api/postgen":
            topic = params.get("message", params.get("topic", ""))
            if not topic:
                json_response(self, {"error": "請提供出post嘅主題"}, 400)
                return
            log(f"PostGen: {topic[:80]}...")
            reply = call_llm(POSTGEN_PROMPT, f"主題：{topic}", temperature=0.9, max_tokens=800)
            json_response(self, {"agent": "PostGen", "reply": reply})

        # ──── Contact Form (existing) ────
        elif path == "/contact":
            name = params.get("name", "").strip()
            phone = params.get("phone", "").strip()
            message = params.get("message", "").strip()
            if not name:
                json_response(self, {"success": False, "error": "請填寫你嘅名"}, 400); return
            if not phone:
                json_response(self, {"success": False, "error": "請填寫電話 / WhatsApp"}, 400); return
            if not message:
                json_response(self, {"success": False, "error": "請填寫想查詢嘅內容"}, 400); return

            log(f"📨 Inquiry: {name} | {phone} | {message[:60]}...")
            tg_ok = send_telegram(name, phone, message)
            json_response(self, {
                "success": True,
                "message": "查詢已送出！港力團隊會盡快聯絡你 🦾",
                "telegram_sent": tg_ok,
            })

        else:
            json_response(self, {"error": "not found"}, 404)

    def log_message(self, format, *args):
        pass

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    log("🦾 港力工程 AI Server v2.0 starting...")
    log(f"   Agents: QuoteBot | SaveCalc | BookMate | HelpBot | RankUp | PostGen")
    log(f"   Port: {PORT}")
    log(f"   LLM: {LLM_MODEL} @ {LLM_BASE_URL}")
    log(f"   API Key: {'✅ configured' if LLM_API_KEY else '❌ NOT SET (agents offline)'}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
