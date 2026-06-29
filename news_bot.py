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


# =========================
# 환경변수
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

print("BOT_TOKEN exists:", bool(BOT_TOKEN))
print("CHANNEL_ID:", CHANNEL_ID)

if not BOT_TOKEN or not CHANNEL_ID:
    print("ERROR: BOT_TOKEN or CHANNEL_ID is missing")
    exit()


# =========================
# 설정
# =========================
TIMEZONE = ZoneInfo("Asia/Seoul")
BRIEFING_HOUR = 9
CHECK_INTERVAL = 300  # 5분

SENT_FILE = "sent_dates.json"


# =========================
# RSS 피드
# =========================
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=한전+부채&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=국민연금+기후&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=석탄발전&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=탈석탄&hl=ko&gl=KR&ceid=KR:ko",
]


# =========================
# 키워드
# =========================
KEYWORDS = [
    "한전 부채",
    "한전채",
    "국민연금 기후",
    "석탄발전",
    "탈석탄",
    "삼척블루파워 회사채",
]


# =========================
# Health Server (Render용)
# =========================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot running")

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Health server running on port {port}")
    server.serve_forever()


# =========================
# 유틸
# =========================
def normalize(text):
    return text.replace(" ", "").lower()


def contains_keyword(text):
    t = normalize(text)
    return any(normalize(k) in t for k in KEYWORDS)


def article_hash(title, link):
    return hashlib.md5(f"{title}|{link}".encode()).hexdigest()


def load_sent_dates():
    if not os.path.exists(SENT_FILE):
        return []
    try:
        return json.load(open(SENT_FILE, "r"))
    except:
        return []


def save_sent_date(date):
    data = load_sent_dates()
    if date not in data:
        data.append(date)
    json.dump(data, open(SENT_FILE, "w"), indent=2)


def already_sent_today(date):
    return date in load_sent_dates()


# =========================
# ✅ 핵심: 24시간 필터 적용
# =========================
def fetch_articles():
    articles = []
    seen = set()

    now = datetime.now(timezone.utc)

    for feed_url in RSS_FEEDS:
        print("Fetching:", feed_url)

        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:20]:

            title = getattr(entry, "title", "")
            link = getattr(entry, "link", "")

            if not title or not link:
                continue

            # ✅ 날짜 필터
            published = getattr(entry, "published_parsed", None)

            if published:
                pub_date = datetime(*published[:6], tzinfo=timezone.utc)

                # ✅ 24시간 초과 기사 제외
                if (now - pub_date).total_seconds() > 86400:
                    continue

            # ✅ 키워드 필터
            if not contains_keyword(title):
                continue

            key = article_hash(title, link)
            if key in seen:
                continue

            seen.add(key)

            articles.append({
                "title": title,
                "link": link
            })

    return articles[:10]


# =========================
# 텔레그램
# =========================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    res = requests.post(url, data=data)
    print("Telegram:", res.text)
    return res.status_code == 200


# =========================
# 메시지 생성
# =========================
def build_message(articles):

    date = datetime.now(TIMEZONE).strftime("%Y-%m-%d")

    if not articles:
        return f"""
🇰🇷 <b>SFOC Climate Finance Briefing</b>
📅 {date}

24시간 내 관련 뉴스 없음
"""

    msg = f"""
🇰🇷 <b>SFOC Climate Finance Briefing</b>
📅 {date}

오늘 기사 {len(articles)}건
"""

    for i, a in enumerate(articles, 1):
        msg += f"\n\n<b>{i}. {escape(a['title'])}</b>\n👉 {a['link']}"

    return msg


# =========================
# 메인 루프
# =========================
def briefing_loop():

    print("Starting loop")

    while True:
        now = datetime.now(TIMEZONE)
        today = now.strftime("%Y-%m-%d")

        print("Current:", now)

        if now.hour >= BRIEFING_HOUR and not already_sent_today(today):
            print("Sending briefing...")

            articles = fetch_articles()
            message = build_message(articles)

            if send_telegram(message):
                save_sent_date(today)

        time.sleep(CHECK_INTERVAL)


# =========================
# 실행
# =========================
if __name__ == "__main__":

    # Health server (Render)
    threading.Thread(target=start_health_server, daemon=True).start()

    briefing_loop()