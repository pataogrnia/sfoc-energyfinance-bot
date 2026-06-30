import os
import time
import json
import hashlib
import threading
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer
from html import escape

import requests
import feedparser

# ===== 환경변수 =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

print("BOT_TOKEN exists:", bool(BOT_TOKEN))
print("CHANNEL_ID:", CHANNEL_ID)

if not BOT_TOKEN or not CHANNEL_ID:
    print("ERROR: Missing env variables")
    exit()

# ===== 설정 =====
TIMEZONE = ZoneInfo("Asia/Seoul")
BRIEFING_HOUR = 9
CHECK_INTERVAL = 300  # 5분

SENT_FILE = "sent_dates.json"

# ===== RSS =====
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=한전+부채&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=국민연금+기후&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=석탄발전&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=탈석탄&hl=ko&gl=KR&ceid=KR:ko",
]

# ✅ ✅ AND 조건 키워드

KEYWORD_GROUPS = [
    ["한전", "부채"],             # 둘 다 포함
    ["한전채"],                  # 단일
    ["석탄", "발전"],            # 둘 다 포함
    ["탈석탄"],                  # 단일
    ["석탄화력"],                # 단일
    ["삼척블루파워", "사채"],    # 둘 다 포함
    ["국민연금", "기후"],        # 둘 다 포함
    ["보험", "기후"],            # 둘 다 포함
    ["은행", "기후"]             # 둘 다 포함
]


# ===== Health Server =====
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return

def start_server():
    port = int(os.getenv("PORT", "10000"))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()

# ===== 유틸 =====
def normalize(text):
    return text.replace(" ", "").lower()

def contains_keyword(text):
    text_clean = normalize(text)

    for group in KEYWORD_GROUPS:
        if all(normalize(k) in text_clean for k in group):
            return True

    return False

def hash_key(title, link):
    return hashlib.md5(f"{title}|{link}".encode()).hexdigest()

def load_sent():
    if not os.path.exists(SENT_FILE):
        return []
    return json.load(open(SENT_FILE))

def save_sent(date):
    data = load_sent()
    if date not in data:
        data.append(date)
    json.dump(data, open(SENT_FILE, "w"))

def sent_today(date):
    return date in load_sent()

# ===== 뉴스 =====
def fetch_articles():
    articles = []
    seen = set()

    now = datetime.now(timezone.utc)

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for e in feed.entries[:20]:
            title = getattr(e, "title", "")
            link = getattr(e, "link", "")

            if not title or not link:
                continue

            # ✅ 24시간 필터
            pub = getattr(e, "published_parsed", None)
            if pub:
                pub_time = datetime(*pub[:6], tzinfo=timezone.utc)
                if (now - pub_time).total_seconds() > 86400:
                    continue

            # ✅ 키워드 필터
            if not contains_keyword(title):
                continue

            key = hash_key(title, link)
            if key in seen:
                continue

            seen.add(key)

            articles.append({
                "title": title,
                "link": link
            })

    return articles[:10]

# ===== 텔레그램 =====
def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    res = requests.post(url, data={
        "chat_id": CHANNEL_ID,
        "text": msg,
        "parse_mode": "HTML"
    })
    print(res.text)
    return res.status_code == 200

# ===== 메시지 =====
def build(articles):
    date = datetime.now(TIMEZONE).strftime("%Y-%m-%d")

    msg = f"🇰🇷 <b>SFOC Climate Finance Briefing</b>\n📅 {date}\n"

    for i, a in enumerate(articles, 1):
        msg += f"\n\n<b>{i}. {escape(a['title'])}</b>\n👉 {a['link']}"

    return msg

# ===== 루프 =====
def loop():

    while True:

        now = datetime.now(TIMEZONE)
        today = now.strftime("%Y-%m-%d")

        if now.hour >= BRIEFING_HOUR and not sent_today(today):

            print("Sending briefing...")

            articles = fetch_articles()
            msg = build(articles)

            if send(msg):
                save_sent(today)

        time.sleep(CHECK_INTERVAL)

# ===== 실행 =====
if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    loop()
