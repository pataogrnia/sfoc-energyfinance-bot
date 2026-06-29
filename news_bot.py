import requests
import feedparser
import time
import hashlib
import os

# ===== 환경변수 =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# ✅ 디버그 출력 (중요)
print("BOT_TOKEN:", BOT_TOKEN)
print("CHANNEL_ID:", CHANNEL_ID)

if not BOT_TOKEN or not CHANNEL_ID:
    print("ERROR: BOT_TOKEN or CHANNEL_ID is missing")
    exit()

# ===== RSS 설정 =====
GLOBAL_FEEDS = [
    "https://news.google.com/rss/search?q=coal+phase-out&hl=en-US&gl=US&ceid=US:en",
    "https://www.reuters.com/business/energy/rss"
]

KOREA_FEEDS = [
    "https://news.google.com/rss/search?q=한전+부채&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=국민연금+기후&hl=ko&gl=KR&ceid=KR:ko"
]

# ===== 키워드 =====
KEYWORDS = [
    "한전 부채",
    "국민연금 기후",
    "석탄발전",
    "탈석탄"
]

CHECK_INTERVAL = 600  # 10분

posted = set()

# ===== 텔레그램 전송 =====
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": CHANNEL_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        res = requests.post(url, data=data)
        print("Telegram response:", res.text)
    except Exception as e:
        print("Telegram send error:", e)

# ===== 키워드 필터 =====
def contains_keyword(text):
    text = text.replace(" ", "")
    keywords_processed = [k.replace(" ", "") for k in KEYWORDS]
    return any(k in text for k in keywords_processed)

# ===== 중복 방지 =====
def hash_title(title):
    return hashlib.md5(title.encode()).hexdigest()

# ===== 뉴스 처리 =====
def process_feed(feed_url, region):
    try:
        feed = feedparser.parse(feed_url)
        print("Fetching:", feed_url)

        for entry in feed.entries[:5]:
            title = entry.title
            link = entry.link

            print("Checking:", title)

            if not contains_keyword(title):
                continue

            key = hash_title(title)
            if key in posted:
                continue

            posted.add(key)

            label = "🇰🇷 Korea" if region == "KR" else "🌏 Global"

            message = f"""
{label} <b>Climate Finance News</b>

<b>{title}</b>

👉 {link}
"""

            send_telegram(message)
            print("Sent:", title)

    except Exception as e:
        print("Feed error:", e)

# ===== 메인 =====
while True:
    print("=== RUNNING LOOP ===")

    try:
        for f in GLOBAL_FEEDS:
            process_feed(f, "GLOBAL")

        for f in KOREA_FEEDS:
            process_feed(f, "KR")

    except Exception as e:
        print("Main loop error:", e)

    time.sleep(CHECK_INTERVAL)
