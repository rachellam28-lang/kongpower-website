"""
港力工程 HelpBot — Telegram AI 客服
=====================================
@kongpower_invoice_bot 自動回答太陽能 FAQ
用法：python helpbot.py
"""
import json, time, sys, os
from datetime import datetime
import http.client

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
BOT_TOKEN = "8264433914:AAG6K1Tve0_mCl0Io4Z2omxFu5aWKeg7V8U"
BOT_NAME = "@kongpower_invoice_bot"

# ---------------------------------------------------------------------------
# FAQ Database — keyword → reply
# ---------------------------------------------------------------------------
FAQ = [
    {
        "keywords": ["幾錢", "價錢", "費用", "成本", "budget", "price", "報價", "收費", "貴唔貴", "平"],
        "reply": (
            "💰 <b>太陽能系統價錢</b>\n\n"
            "村屋常見系統：\n"
            "• <b>5 kW</b> — 約 $80,000 – $100,000\n"
            "• <b>8 kW</b> — 約 $120,000 – $150,000\n"
            "• <b>10 kW</b> — 約 $150,000 – $180,000\n\n"
            "以上係連安裝 + FiT 申請一條龍全包價。\n"
            "實際價錢視乎屋頂狀況、日照角度、結構承重，\n"
            "港力提供<b>免費上門評估</b>，即場話你知幾錢。\n\n"
            "📞 想即時傾？填網站 form 或者 WhatsApp 我哋！"
        ),
    },
    {
        "keywords": ["回本", "幾耐", "回報", "賺", "收入", "ROI", "payback", "賺幾多"],
        "reply": (
            "📊 <b>回本期 & 收入</b>\n\n"
            "以一個典型 <b>8 kW 村屋系統</b>為例：\n"
            "• 年發電量：約 9,500 度\n"
            "• 年 FiT 收入：約 <b>$28,500</b>\n"
            "• 回本期：約 <b>4–5 年</b>\n"
            "• 25 年總收益：約 <b>$712,500</b>\n\n"
            "政府上網電價計劃 (FiT) 延至 <b>2033 年</b>，\n"
            "越早裝越賺！回本後淨賺 15-20 年 💰\n\n"
            "想知你間屋實際回報？用 /calc 計數機！"
        ),
    },
    {
        "keywords": ["FiT", "上網電價", "政府", "補貼", "電費", "中電", "港燈", "申請"],
        "reply": (
            "📝 <b>FiT 上網電價計劃</b>\n\n"
            "• 由 <b>中電 / 港燈</b> 營運至 <b>2033 年</b>\n"
            "• 你發出嘅太陽能電賣俾電力公司\n"
            "• 現行電價約 <b>$3 – $5 / 度</b>（視乎系統大小）\n\n"
            "港力一條龍幫你搞：\n"
            "1️⃣ 入紙申請\n"
            "2️⃣ 提交圖則\n"
            "3️⃣ 安裝 + 申報\n"
            "4️⃣ 併網測試\n"
            "5️⃣ 開始收錢 💰\n\n"
            "成個過程約 <b>2–3 個月</b>，你完全唔使煩！"
        ),
    },
    {
        "keywords": ["安裝", "程序", "流程", "點裝", "點搞", "步驟", "process"],
        "reply": (
            "🔧 <b>安裝流程 — 5 步搞掂</b>\n\n"
            "1️⃣ <b>WhatsApp 查詢</b> → 約上門睇位\n"
            "2️⃣ <b>港力親身上門</b> → 檢查天台、日照、結構\n"
            "3️⃣ <b>即時報價</b> → 出詳細方案 + FiT 申請\n"
            "4️⃣ <b>專業施工</b> → 約 1-3 星期完成\n"
            "5️⃣ <b>併網 + 開始收錢</b> → 港力幫你搞晒\n\n"
            "全個過程約 <b>2 個月</b>，一條龍唔使煩 🔥"
        ),
    },
    {
        "keywords": ["保養", "保用", "warranty", "維修", "壞", "幾年", "壽命", "20年", "25年"],
        "reply": (
            "🛡️ <b>保養 & 壽命</b>\n\n"
            "• 太陽能板壽命：<b>25–30 年</b>\n"
            "• 發電保證：<b>20 年</b>（80% 以上輸出）\n"
            "• 逆變器壽命：約 <b>10–15 年</b>\n\n"
            "港力提供<b>20 年全面保養</b>：\n"
            "• AI 系統 24/7 監控發電狀況\n"
            "• 有異常即時 alert，未壞先修\n"
            "• 有咩事 WhatsApp 即覆\n\n"
            "裝完就唔使煩，我哋幫你睇到實 🔍"
        ),
    },
    {
        "keywords": ["天台", "屋頂", "啱唔啱", "夠唔夠", "方向", "日照", "唔夠光", "向北"],
        "reply": (
            "🏠 <b>你個天台啱唔啱裝？</b>\n\n"
            "大部分新界村屋、屋苑天台都啱裝：\n"
            "• 最少 <b>200 平方呎</b> 可用面積\n"
            "• 天台結構承重 OK\n"
            "• 冇嚴重遮擋（樹木、大廈）\n\n"
            "就算向北都裝得！向南最好但唔係必須。\n\n"
            "港力提供<b>免費上門評估</b>，用 AI 分析：\n"
            "🔍 日照角度 | 🏗️ 結構承重 | 📐 最佳佈局\n"
            "3 個工作天出書面報告 ✍️"
        ),
    },
    {
        "keywords": ["防水", "隔熱", "漏水", "滲水", "熱"],
        "reply": (
            "🛡️ <b>天台防水 + 隔熱</b>\n\n"
            "裝太陽能板前<b>強烈建議</b>先做好防水！\n\n"
            "港力提供一條龍服務：\n"
            "• 德國 PU 防水膠膜\n"
            "• 反射隔熱塗層（降溫 5°C）\n"
            "• 10 年防水保證\n"
            "• 兼顧太陽能基座安裝\n\n"
            "先防水 → 再裝板 → 萬無一失 ✅"
        ),
    },
    {
        "keywords": ["學校", "村屋", "屋苑", "工廈", "私樓", "邊度", "做邊", "服務"],
        "reply": (
            "📍 <b>服務範圍 — 全香港</b>\n\n"
            "港力服務全港各區：\n"
            "🏘️ <b>村屋</b> — 我哋做最多，新界各區都有案例\n"
            "🏫 <b>學校</b> — 禮堂天台、停車場上蓋\n"
            "🏢 <b>屋苑</b> — 法團項目經驗豐富\n"
            "🏠 <b>私樓</b> — 天台業權清晰就做得\n"
            "🏭 <b>工廈</b> — 大面積高回報\n\n"
            "邊度都去！免費上門評估 🚗"
        ),
    },
]

# ---------------------------------------------------------------------------
# Default / fallback reply
# ---------------------------------------------------------------------------
DEFAULT_REPLY = (
    "🤖 <b>港力工程 AI 客服</b>\n\n"
    "你好！我係港力嘅 HelpBot 🦾\n"
    "可以答你有關太陽能嘅問題：\n\n"
    "💰 幾錢？｜📊 幾耐回本？\n"
    "📝 FiT 點申請？｜🔧 點安裝？\n"
    "🏠 我個天台啱唔啱？｜🛡️ 保養幾耐？\n\n"
    "直接打字問我啦！想搵真人就填網站 form 😊"
)

WELCOME_MSG = (
    "☀️ <b>港力工程 — AI 客服</b>\n\n"
    "你好！有咩關於太陽能想問？\n\n"
    "你可以問我：\n"
    "• 裝太陽能幾錢？\n"
    "• 幾耐回本？\n"
    "• 我個天台啱唔啱裝？\n"
    "• FiT 點申請？\n\n"
    "直接打字就得 👇"
)

# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------
def find_reply(text: str) -> str:
    """Match user message to FAQ, return best reply."""
    text_lower = text.lower()
    for item in FAQ:
        for kw in item["keywords"]:
            if kw.lower() in text_lower:
                return item["reply"]
    return None

def handle_command(text: str) -> str | None:
    """Handle /commands."""
    cmd = text.strip().lower()
    if cmd == "/start":
        return WELCOME_MSG
    if cmd in ("/help", "help", "hi", "hello", "你好", "哈囉"):
        return WELCOME_MSG
    if cmd == "/calc":
        return (
            "🧮 <b>回本計算機</b>\n\n"
            "以 500 ft² 村屋天台為例：\n"
            "• 可裝 8 kW 系統\n"
            "• 年發電 ≈ 9,500 度\n"
            "• 年收入 ≈ $28,500\n"
            "• 4–5 年回本\n"
            "• 25 年總收益 ≈ $712,500\n\n"
            "想知你間屋嘅實際數字？\n"
            "填網站 form，港力幫你度身計！ 📋"
        )
    if cmd in ("/contact", "/book", "預約", "約"):
        return (
            "📅 <b>預約免費上門評估</b>\n\n"
            "填網站聯絡表單，港力團隊會盡快覆你：\n"
            "💬 講低你個名 + 電話 + 地址\n"
            "👷 港力親自上門睇位\n"
            "📋 即場報價\n\n"
            "或者直接填我哋網站 form 👇"
        )
    return None

# ---------------------------------------------------------------------------
# Telegram API
# ---------------------------------------------------------------------------
def call_api(method: str, data: dict) -> dict:
    """Call Telegram Bot API."""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    conn = http.client.HTTPSConnection("api.telegram.org", timeout=10)
    conn.request("POST", f"/bot{BOT_TOKEN}/{method}", body=body,
                 headers={"Content-Type": "application/json; charset=utf-8"})
    resp = conn.getresponse()
    result = json.loads(resp.read())
    conn.close()
    return result

def send_message(chat_id: int, text: str):
    """Send a message to a chat."""
    return call_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    })

# ---------------------------------------------------------------------------
# Main polling loop
# ---------------------------------------------------------------------------
def main():
    sys.stdout.flush()
    print(f"🤖 港力 HelpBot 啟動中... {BOT_NAME}", flush=True)
    print("   客人 send message 畀 bot → 自動秒回", flush=True)
    print("   按 Ctrl+C 停止\n", flush=True)

    last_update_id = 0

    while True:
        try:
            result = call_api("getUpdates", {
                "offset": last_update_id + 1,
                "timeout": 30,
            })

            if result.get("ok"):
                for update in result["result"]:
                    last_update_id = update["update_id"]

                    msg = update.get("message")
                    if not msg:
                        continue

                    chat_id = msg["chat"]["id"]
                    text = msg.get("text", "").strip()

                    if not text:
                        continue

                    now = datetime.now().strftime("%H:%M:%S")
                    user = msg["from"].get("first_name", "客人")
                    print(f"[{now}] {user}: {text[:60]}")

                    # Find reply
                    reply = handle_command(text) or find_reply(text) or DEFAULT_REPLY
                    send_message(chat_id, reply)
                    print(f"[{now}]   → HelpBot 已回覆")

        except KeyboardInterrupt:
            print("\n👋 HelpBot 已停止")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
